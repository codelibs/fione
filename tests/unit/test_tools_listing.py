"""The listing tools, the project scope of a tool call and the channel in the call log."""

import logging
from types import SimpleNamespace

import pandas as pd
import pytest

from fione import db
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.models import service as models
from fione.projects import ingest
from fione.projects import service as projects
from fione.projects.service import DatasetType
from fione.storage import LocalStorage
from fione.tools import ToolContext, ToolError, call_tool, list_tools, registry
from fione.tools.registry import DATA_NOTICE, NOT_ALLOWED

TOOL_NAMES = {
    "describe_dataset",
    "get_column_stats",
    "get_leaderboard",
    "get_feature_importance",
    "get_model_diagnostics",
    "get_partial_dependence",
    "get_training_events",
    "propose_training_config",
    "list_projects",
    "list_datasets",
    "list_models",
}
EVIL_NAME = "a\n<script>x</script>\tb"


def add_model(conn, project, dataset, name="m"):
    return models.insert_model(
        conn,
        project_id=project.id,
        dataset_id=dataset.id,
        job_id=None,
        name=name,
        task="classification",
        target="label",
        best_model="Ensemble",
        stop_reason="max_models",
        storage_prefix="projects/x/models/m/",
        trusted=True,
        config={},
        leaderboard=[{"model": "Ensemble", "weight": 1.0}],
        trials=[],
        metrics={"accuracy": 0.9},
        importance={},
    )


@pytest.fixture
def env(tmp_path):
    conn = db.connect(tmp_path / "fione.db")
    db.migrate(conn)
    storage = LocalStorage(tmp_path / "storage")
    users = SimpleNamespace(
        owner=auth.create_user(conn, "owner", "pw-owner-1", Role.EDITOR),
        viewer=auth.create_user(conn, "viewer", "pw-viewer-1", Role.VIEWER),
        outsider=auth.create_user(conn, "outsider", "pw-outsider-1", Role.EDITOR),
        admin=auth.create_user(conn, "admin", "pw-admin-1", Role.ADMIN),
    )
    frame = pd.DataFrame({"x": range(30), "label": ["a", "b"] * 15})
    a = projects.create_project(conn, users.owner, "Project A")
    b = projects.create_project(conn, users.owner, "Project B")
    projects.share_project(conn, users.owner, a.id, "viewer", ProjectAccess.VIEWER)
    ds_a = ingest.ingest_batches(storage, conn, a.id, "alpha", DatasetType.TRAIN, [frame])
    ds_b = ingest.ingest_batches(storage, conn, b.id, EVIL_NAME, DatasetType.TRAIN, [frame])
    model_a = add_model(conn, a, ds_a, "model-a")
    model_b = add_model(conn, b, ds_b, "model-b")
    job_b = store.enqueue(conn, "automl", b.id, users.owner.id, {})
    job_none = store.enqueue(conn, "module", None, users.owner.id, {})
    yield SimpleNamespace(
        conn=conn, storage=storage, users=users, a=a, b=b, ds_a=ds_a, ds_b=ds_b,
        model_a=model_a, model_b=model_b, job_b=job_b, job_none=job_none,
    )  # fmt: skip
    conn.close()


def call(env, name, args, user=None, **ctx):
    context = ToolContext(env.conn, env.storage, user or env.users.owner, **ctx)
    return call_tool(name, args, context)


def test_registry_has_the_eleven_flat_tools():
    tools = {t["function"]["name"]: t["function"] for t in list_tools()}
    assert set(tools) == TOOL_NAMES and len(list_tools()) == 11
    for name, fn in tools.items():
        assert registry._TOOLS[name].read_only is True
        schema = fn["parameters"]
        assert schema["additionalProperties"] is False
        assert all(
            p["type"] in {"string", "integer", "number", "boolean"}
            for p in schema["properties"].values()
        )
    assert tools["list_projects"]["parameters"]["properties"] == {}
    for name in ("list_datasets", "list_models"):
        project_id = tools[name]["parameters"]["properties"]["project_id"]
        assert project_id["type"] == "string" and project_id["maxLength"] == 64
        assert tools[name]["parameters"]["required"] == ["project_id"]


def test_listing_follows_permissions(env):
    owner = call(env, "list_projects", {})
    assert owner["_data_notice"] == DATA_NOTICE
    by_id = {p["id"]: p for p in owner["projects"]}
    assert by_id[env.a.id] == {
        "id": env.a.id,
        "name": "Project A",
        "access": "owner",
        "n_datasets": 1,
        "n_models": 1,
    }
    assert {p["id"]: p["access"] for p in owner["projects"]} == {
        env.a.id: "owner",
        env.b.id: "owner",
    }

    viewer = call(env, "list_projects", {}, user=env.users.viewer)
    assert [(p["id"], p["access"]) for p in viewer["projects"]] == [(env.a.id, "viewer")]
    admin = call(env, "list_projects", {}, user=env.users.admin)
    assert {p["access"] for p in admin["projects"]} == {"admin"}
    assert call(env, "list_projects", {}, user=env.users.outsider)["projects"] == []

    outsider = ToolContext(env.conn, env.storage, env.users.outsider)
    for name in ("list_datasets", "list_models"):
        with pytest.raises(ToolError, match=NOT_ALLOWED):
            call_tool(name, {"project_id": env.a.id}, outsider)
        with pytest.raises(ToolError, match=NOT_ALLOWED):
            call_tool(name, {"project_id": "no-such-project"}, outsider)
    datasets = call(env, "list_datasets", {"project_id": env.a.id}, user=env.users.viewer)
    assert datasets["datasets"] == [
        {"id": env.ds_a.id, "name": "alpha", "type": "train", "n_rows": 30, "n_cols": 2}
    ]
    listed = call(env, "list_models", {"project_id": env.a.id}, user=env.users.viewer)["models"]
    assert listed == [
        {
            "id": env.model_a.id,
            "name": "model-a",
            "task": "classification",
            "target": "label",
            "dataset_id": env.ds_a.id,
            "best_model": "Ensemble",
        }
    ]


def test_project_scope_refuses_other_projects(env):
    kw = {"project_id": env.a.id}
    refused = [
        ("describe_dataset", {"dataset_id": env.ds_b.id}),
        ("get_leaderboard", {"model_id": env.model_b.id}),
        ("get_feature_importance", {"model_id": env.model_b.id}),
        ("get_model_diagnostics", {"model_id": env.model_b.id}),
        ("get_partial_dependence", {"model_id": env.model_b.id, "column": "x"}),
        ("list_datasets", {"project_id": env.b.id}),
        ("list_models", {"project_id": env.b.id}),
        ("get_training_events", {"job_id": env.job_b.id}),
        ("get_training_events", {"job_id": env.job_none.id}),
        ("propose_training_config", {"dataset_id": env.ds_b.id, "target": "label"}),
    ]
    for name, args in refused:
        with pytest.raises(ToolError, match=NOT_ALLOWED):
            call(env, name, args, **kw)
    # the same calls without a scope: the owner may read the project's objects
    assert call(env, "describe_dataset", {"dataset_id": env.ds_b.id})["dataset"]["id"]
    assert call(env, "get_leaderboard", {"model_id": env.model_b.id})["model"]["id"]
    assert call(env, "list_datasets", {"project_id": env.b.id})["datasets"]

    assert [p["id"] for p in call(env, "list_projects", {}, **kw)["projects"]] == [env.a.id]
    assert call(env, "describe_dataset", {"dataset_id": env.ds_a.id}, **kw)["dataset"]["id"]
    assert call(env, "list_datasets", {"project_id": env.a.id}, **kw)["datasets"]

    # an admin is held to the scope too, and a project-less job is never reachable
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call(env, "get_training_events", {"job_id": env.job_none.id}, env.users.admin, **kw)
    assert call(env, "get_training_events", {"job_id": env.job_none.id}, env.users.admin)["job"]

    # losing read access ends the scope's reach
    projects.unshare_project(env.conn, env.users.owner, env.a.id, "viewer")
    viewer = ToolContext(env.conn, env.storage, env.users.viewer, project_id=env.a.id)
    assert call_tool("list_projects", {}, viewer)["projects"] == []
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call_tool("list_datasets", {"project_id": env.a.id}, viewer)


def test_listing_names_are_cleaned(env):
    result = call(env, "list_datasets", {"project_id": env.b.id})
    assert result["_data_notice"] == DATA_NOTICE
    assert result["datasets"][0]["name"] == "a <script>x</script> b"
    projects.create_project(env.conn, env.users.owner, "p\nq\tr")
    names = [p["name"] for p in call(env, "list_projects", {})["projects"]]
    assert "p q r" in names
    add_model(env.conn, env.b, env.ds_b, "m\n<b>x</b>")
    assert "m <b>x</b>" in [
        m["name"] for m in call(env, "list_models", {"project_id": env.b.id})["models"]
    ]


def test_listings_are_cut(env, monkeypatch):
    for i in range(3):
        projects.create_project(env.conn, env.users.owner, f"extra {i}")
        ingest.ingest_batches(
            env.storage,
            env.conn,
            env.b.id,
            f"more {i}",
            DatasetType.TRAIN,
            [pd.DataFrame({"x": [1]})],
        )
        add_model(env.conn, env.b, env.ds_b, f"more {i}")
    monkeypatch.setattr("fione.tools.builtin._MAX_PROJECTS", 3)
    monkeypatch.setattr("fione.tools.builtin._MAX_DATASETS", 2)
    monkeypatch.setattr("fione.tools.builtin._MAX_MODELS", 2)
    projects_ = call(env, "list_projects", {})
    assert len(projects_["projects"]) == 3 and projects_["truncated_lists"] == ["projects"]
    datasets = call(env, "list_datasets", {"project_id": env.b.id})
    assert len(datasets["datasets"]) == 2 and datasets["truncated_lists"] == ["datasets"]
    listed = call(env, "list_models", {"project_id": env.b.id})
    assert len(listed["models"]) == 2 and listed["truncated_lists"] == ["models"]
    # the rest is counted, as describe_dataset does for the columns it leaves out
    assert projects_["n_more_projects"] == 5 - 3  # a, b and three extras
    assert datasets["n_more_datasets"] == 4 - 2
    assert listed["n_more_models"] == 4 - 2


def test_the_access_label_is_the_effective_level(env):
    """A global viewer is held to viewer even in a project they own; an administrator who
    owns a project is its owner; one who has no part in it is labelled admin."""
    maker = auth.create_user(env.conn, "maker", "pw-maker-1", Role.EDITOR)
    mine = projects.create_project(env.conn, maker, "Maker's")
    assert call(env, "list_projects", {}, user=maker)["projects"][0]["access"] == "owner"
    auth.set_role(env.conn, maker.id, Role.VIEWER)
    demoted = auth.get_user(env.conn, maker.id)
    assert [p["access"] for p in call(env, "list_projects", {}, user=demoted)["projects"]] == [
        "viewer"
    ]
    boss = projects.create_project(env.conn, env.users.admin, "Admin's")
    labels = {
        p["id"]: p["access"]
        for p in call(env, "list_projects", {}, user=env.users.admin)["projects"]
    }
    assert labels[boss.id] == "owner" and labels[mine.id] == "admin"


def test_log_names_the_channel(env, caplog):
    with caplog.at_level(logging.INFO, logger="fione.tools"):
        call(env, "list_projects", {}, via="mcp")
        call(env, "list_projects", {})
    lines = [r.getMessage() for r in caplog.records if r.name == "fione.tools"]
    assert "via=mcp" in lines[0] and "via=test" in lines[1]

"""The MCP action tools: off unless FIONE_MCP_WRITE_ENABLED, never in the chat, and each runs
as the token's user with the write access the REST routes ask for."""

from contextlib import closing

import pytest
from test_mcp import bearer, call, iris_dataset, post, rpc

from api_helpers import add_user, connect
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.projects import service as projects
from fione.tools import list_actions, list_tools, registry

ACTIONS = {"list_modules", "start_training", "start_batch_predict", "run_module"}
CONFIG = {"target": "species", "max_runtime_secs": 30}


@pytest.fixture
def writes(make_client):
    client = make_client(mcp_enabled=True, mcp_write_enabled=True)
    user = add_user(client, "ed", Role.EDITOR)
    return client, user


def tool_list(client, headers):
    r = post(client, rpc("tools/list"), headers)
    return {t["name"]: t for t in r.json()["result"]["tools"]}


def jobs(client):
    with closing(connect(client)) as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM jobs ORDER BY id")]
        return [store.get_job(conn, i) for i in ids]


def test_actions_are_not_chat_tools():
    assert {t.name for t in list_actions()} == ACTIONS
    assert not ACTIONS & {t["function"]["name"] for t in list_tools()}
    assert not ACTIONS & set(registry._TOOLS)


def test_off_by_default(make_client):
    client = make_client(mcp_enabled=True)
    user = add_user(client, "ed", Role.EDITOR)
    headers = bearer(client, user)
    assert not ACTIONS & set(tool_list(client, headers))
    result = call(client, headers, "list_modules")
    assert result["isError"] is True and result["content"][0]["text"] == "unknown tool"
    init = post(client, rpc("initialize", {"protocolVersion": "2025-06-18"}), headers)
    assert init.json()["result"]["instructions"].startswith("Read-only")


def test_listed_with_honest_annotations(writes):
    client, user = writes
    tools = tool_list(client, bearer(client, user))
    assert ACTIONS <= set(tools) and "list_projects" in tools
    assert tools["list_modules"]["annotations"]["readOnlyHint"] is True
    for name in ACTIONS - {"list_modules"}:
        ann = tools[name]["annotations"]
        assert ann["readOnlyHint"] is False and ann["destructiveHint"] is False
        assert ann["idempotentHint"] is False
    assert tools["list_projects"]["annotations"]["readOnlyHint"] is True
    assert tools["start_training"]["inputSchema"]["properties"]["config"]["type"] == "object"


def test_start_training_queues_a_job(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    result = call(
        client,
        headers,
        "start_training",
        {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG, "name": "t"},
    )
    assert result["isError"] is False, result
    out = result["structuredContent"]
    (job,) = jobs(client)
    assert out["job_id"] == job.id and out["kind"] == "automl" and out["status"] == "queued"
    assert job.owner_id == user.id and job.payload["name"] == "t"
    assert job.payload["config"]["target"] == "species"


def test_bad_config_is_a_message_and_queues_nothing(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    result = call(
        client,
        bearer(client, user),
        "start_training",
        {"project_id": project.id, "dataset_id": dataset.id, "config": {"target": "nope"}},
    )
    assert result["isError"] is True and "nope" in result["content"][0]["text"]
    assert jobs(client) == []


def test_arguments_are_checked(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    for args in (
        {"project_id": project.id, "dataset_id": dataset.id},  # no config
        {"project_id": project.id, "dataset_id": dataset.id, "config": []},
        {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG, "x": 1},
    ):
        assert call(client, headers, "start_training", args)["isError"] is True
    assert jobs(client) == []


def test_a_viewer_member_cannot_start_and_a_stranger_sees_nothing(writes):
    client, owner = writes
    project, dataset = iris_dataset(client, owner)
    viewer = add_user(client, "vi", Role.EDITOR)
    stranger = add_user(client, "st", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project.id, "vi", ProjectAccess.VIEWER)
    args = {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG}
    seen = call(client, bearer(client, viewer), "start_training", args)
    assert seen["isError"] is True and "write access" in seen["content"][0]["text"]
    hidden = call(client, bearer(client, stranger), "start_training", args)
    assert hidden["isError"] is True and hidden["content"][0]["text"] == "not found or not allowed"
    missing = call(client, bearer(client, stranger), "start_training", {**args, "project_id": "zz"})
    assert missing["content"] == hidden["content"]
    assert jobs(client) == []


def test_a_shared_editor_can_start(writes):
    client, owner = writes
    project, dataset = iris_dataset(client, owner)
    editor = add_user(client, "e2", Role.EDITOR)
    with closing(connect(client)) as conn:
        projects.share_project(conn, owner, project.id, "e2", ProjectAccess.EDITOR)
    args = {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG}
    assert call(client, bearer(client, editor), "start_training", args)["isError"] is False
    assert [j.owner_id for j in jobs(client)] == [editor.id]


def test_modules_are_listed_and_run(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    listed = call(client, headers, "list_modules")["structuredContent"]["modules"]
    assert listed and all({"id", "params", "builtin"} <= set(m) for m in listed)
    module = next(m for m in listed if m["kind"] == "frame" and not m["params"].get("required"))
    result = call(
        client,
        headers,
        "run_module",
        {"project_id": project.id, "module_id": module["id"], "dataset_id": dataset.id},
    )
    assert result["isError"] is False, result
    assert [j.kind for j in jobs(client)] == ["module"]
    unknown = call(
        client,
        headers,
        "run_module",
        {"project_id": project.id, "module_id": "nope", "dataset_id": dataset.id},
    )
    assert unknown["isError"] is True


def test_batch_predict_needs_a_model_of_the_project(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    result = call(
        client,
        bearer(client, user),
        "start_batch_predict",
        {"project_id": project.id, "model_id": 999, "dataset_id": dataset.id},
    )
    assert result["isError"] is True and jobs(client) == []


def test_a_class_label_is_not_in_a_refusal(writes):
    import io

    from fione.projects.ingest import ingest_csv
    from fione.projects.service import DatasetType

    client, user = writes
    csv = ("x,y\n" + "1,a\n" * 20 + "1,b\n" * 20 + "1,SECRETLABEL\n").encode()
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, "P")
        dataset = ingest_csv(
            client.app.state.storage, conn, project.id, "d", DatasetType.TRAIN, io.BytesIO(csv)
        )
    result = call(
        client,
        bearer(client, user),
        "start_training",
        {"project_id": project.id, "dataset_id": dataset.id, "config": {"target": "y"}},
    )
    assert result["isError"] is True and "SECRETLABEL" not in result["content"][0]["text"]
    assert "only 1 row" in result["content"][0]["text"] and jobs(client) == []


def test_a_job_name_is_trimmed_and_not_empty(writes):
    client, user = writes
    project, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    args = {"project_id": project.id, "dataset_id": dataset.id, "config": CONFIG}
    assert call(client, headers, "start_training", {**args, "name": "   "})["isError"] is True
    assert jobs(client) == []
    assert call(client, headers, "start_training", {**args, "name": " t "})["isError"] is False
    assert jobs(client)[0].payload["name"] == "t"

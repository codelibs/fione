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
from fione.tools import ToolContext, ToolError, builtin, call_tool, list_tools, registry
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
    "find_table_links",
    "propose_join",
    "propose_first_join",
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


def test_registry_has_the_thirteen_flat_tools():
    tools = {t["function"]["name"]: t["function"] for t in list_tools()}
    assert set(tools) == TOOL_NAMES and len(list_tools()) == 14
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


def test_find_table_links_reports_keys_shared_by_datasets(env):
    keys = pd.DataFrame({"Id": range(1, 41), "label": ["a", "b"] * 20})
    events = pd.DataFrame({"id": [i % 40 + 1 for i in range(120)], "amount": range(120)})
    stranger = pd.DataFrame({"id": range(1000, 1040), "z": range(40)})
    for name, frame in (("keys", keys), ("events", events), ("stranger", stranger)):
        ingest.ingest_batches(env.storage, env.conn, env.a.id, name, DatasetType.TRAIN, [frame])
    by_name = {d.name: d.id for d in projects.list_datasets(env.conn, env.a.id)}
    found = call(env, "find_table_links", {"project_id": env.a.id}, user=env.users.viewer)
    assert [link["datasets"] for link in found["links"]] == [[by_name["keys"], by_name["events"]]]
    assert "propose_first_join" in found["next_step"] and "describe_dataset" in found["next_step"]
    link = found["links"][0]
    assert link["columns"] == ["Id", "id"]  # names match without case
    assert link["shared"] == 1.0 and link["relation"] == "one_to_many"
    assert link["one_row_per_key"] == by_name["keys"]
    assert found["sampled"] is False and len(found["datasets"]) == 4
    listed = {d["name"]: d for d in found["datasets"]}
    assert listed["events"]["columns"] == ["id", "amount"]  # which table holds what
    assert "n_more_columns" not in listed["events"]
    outsider = ToolContext(env.conn, env.storage, env.users.outsider)
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call_tool("find_table_links", {"project_id": env.a.id}, outsider)


def test_find_table_links_samples_a_large_dataset_and_reports_repeating_keys(env, monkeypatch):
    monkeypatch.setattr(builtin, "_LINK_FULL_ROWS", 100)
    monkeypatch.setattr(builtin, "_LINK_SAMPLE_ROWS", 60)
    parents = pd.DataFrame({"k": range(1000, 1060), "p": range(60)})
    children = pd.DataFrame({"k": [1000 + i % 60 for i in range(300)], "c": range(300)})
    days = pd.DataFrame({"day": [i % 30 for i in range(100)], "d": range(100)})
    more = pd.DataFrame({"day": [i % 30 for i in range(90)], "m": range(90)})
    for name, frame in (
        ("parents", parents),
        ("children", children),
        ("days", days),
        ("more", more),
    ):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, name, DatasetType.TRAIN, [frame])
    by_name = {d.name: d.id for d in projects.list_datasets(env.conn, env.b.id)}
    found = call(env, "find_table_links", {"project_id": env.b.id})
    relations = {
        (link["column"], link["relation"], link["one_row_per_key"]) for link in found["links"]
    }
    assert relations == {
        ("k", "one_to_many", by_name["parents"]),
        ("day", "many_to_many", None),
    }
    repeating = next(link for link in found["links"] if link["relation"] == "many_to_many")
    assert repeating["one_row_per_key"] is None
    assert found["sampled"] is True


def test_find_table_links_reads_a_key_with_gaps_and_ranks_real_keys_first(env):
    customers = pd.DataFrame({"cid": range(1, 61), "region": ["a", "b", "c"] * 20})
    orders = pd.DataFrame(
        {"cid": pd.array([1 + i % 60 if i % 10 else None for i in range(200)], dtype="Int64")}
    )
    for name, frame in (("customers", customers), ("orders", orders)):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, name, DatasetType.TRAIN, [frame])
    found = call(env, "find_table_links", {"project_id": env.b.id})
    assert [(link["column"], link["relation"]) for link in found["links"]] == [
        ("cid", "one_to_many")
    ]


def test_find_table_links_ranks_one_row_per_key_before_repeating_keys(env):
    wide = {f"f{i}": [j % 40 for j in range(120)] for i in range(8)}
    train = pd.DataFrame({"cid": [1 + j % 50 for j in range(120)], **wide})
    test = pd.DataFrame({"cid": [1 + j % 50 for j in range(120)], **wide})
    people = pd.DataFrame({"cid": range(1, 51), "age": range(50)})
    for name, frame in (("train", train), ("test", test), ("people", people)):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, name, DatasetType.TRAIN, [frame])
    found = call(env, "find_table_links", {"project_id": env.b.id})
    relations = [link["relation"] for link in found["links"]]
    assert relations[:2] == ["one_to_many", "one_to_many"]
    assert relations.count("many_to_many") == 2  # the least certain links are capped


def test_find_table_links_names_the_first_columns_of_a_wide_dataset(env):
    wide = pd.DataFrame({f"c{i}": range(30) for i in range(builtin._LINK_COLUMNS + 5)})
    ingest.ingest_batches(env.storage, env.conn, env.b.id, "wide", DatasetType.TRAIN, [wide])
    found = call(env, "find_table_links", {"project_id": env.b.id})
    block = next(d for d in found["datasets"] if d["name"] == "wide")
    assert block["columns"] == [f"c{i}" for i in range(builtin._LINK_COLUMNS)]
    assert block["n_more_columns"] == 5


def test_find_table_links_cuts_column_names_before_it_cuts_datasets(env):
    for i in range(builtin._LINK_DATASETS):
        frame = pd.DataFrame(
            {f"a_long_column_name_number_{j}": range(30) for j in range(builtin._LINK_COLUMNS)}
        )
        ingest.ingest_batches(env.storage, env.conn, env.b.id, f"d{i}", DatasetType.TRAIN, [frame])
    found = call(env, "find_table_links", {"project_id": env.b.id}, max_result_bytes=3900)
    assert len(found["datasets"]) == builtin._LINK_DATASETS  # every id a link may name is kept
    assert "truncated" not in found and "columns" not in found["datasets"][0]
    full = call(env, "find_table_links", {"project_id": env.b.id})
    assert len(full["datasets"][1]["columns"]) == builtin._LINK_COLUMNS


def test_find_table_links_keeps_a_key_with_stray_repeats_before_categories(env):
    ids = [f"m{i}" for i in range(300)]
    shops = pd.DataFrame(
        {
            "mid": ids + ["m0", "m1"],
            "city": [i % 25 for i in range(302)],
            "zone": [i % 30 for i in range(302)],
        }
    )
    sales = pd.DataFrame(
        {
            "mid": [ids[i % 300] for i in range(600)],
            "city": [i % 25 for i in range(600)],
            "zone": [i % 30 for i in range(600)],
        }
    )
    for name, frame in (("shops", shops), ("sales", sales)):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, name, DatasetType.TRAIN, [frame])
    found = call(env, "find_table_links", {"project_id": env.b.id})
    assert found["links"][0]["column"] == "mid"  # not city or zone, which only a few values share


def _ingest(env, project, **frames):
    for name, frame in frames.items():
        ingest.ingest_batches(env.storage, env.conn, project.id, name, DatasetType.TRAIN, [frame])
    return {d.name: d.id for d in projects.list_datasets(env.conn, project.id)}


def test_find_table_links_matches_a_key_named_for_its_table(env):
    customers = pd.DataFrame({"id": range(1, 61), "city": ["a", "b", "c"] * 20})
    orders = pd.DataFrame({"customer_id": [i % 60 + 1 for i in range(200)], "total": range(200)})
    by_name = _ingest(env, env.b, customers=customers, orders=orders)
    (link,) = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    assert link["datasets"] == [by_name["customers"], by_name["orders"]]
    assert link["columns"] == ["id", "customer_id"] and link["basis"] == "table_id"
    assert link["relation"] == "one_to_many" and link["one_row_per_key"] == by_name["customers"]


def test_find_table_links_matches_similar_names_and_leaves_same_names_unmarked(env):
    people = pd.DataFrame({"cust_id": range(1, 61), "pid": range(100, 160)})
    visits = pd.DataFrame({"customer_id": [i % 60 + 1 for i in range(200)], "pid": range(100, 300)})
    by_name = _ingest(env, env.b, people=people, visits=visits)
    links = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    similar = next(link for link in links if "basis" in link)
    assert similar["columns"] == ["cust_id", "customer_id"] and similar["basis"] == "similar_name"
    same = next(link for link in links if "column" in link)
    assert same["column"] == "pid" and "basis" not in same
    assert {tuple(link["datasets"]) for link in links} == {(by_name["people"], by_name["visits"])}


def test_find_table_links_matches_text_keys_by_their_values_when_the_names_differ(env):
    codes = pd.DataFrame({"serial": [f"s{i:03d}" for i in range(120)], "grade": ["x", "y"] * 60})
    readings = pd.DataFrame({"unit": [f"s{i % 120:03d}" for i in range(360)], "v": range(360)})
    by_name = _ingest(env, env.b, codes=codes, readings=readings)
    (link,) = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    assert link["columns"] == ["serial", "unit"] and link["basis"] == "values"
    assert link["one_row_per_key"] == by_name["codes"] and link["shared"] == 1.0


def test_find_table_links_does_not_match_small_integers_or_unrelated_values(env):
    ranks = pd.DataFrame({"rank": range(40), "name": [f"n{i}" for i in range(40)]})
    counts = pd.DataFrame({"n_items": [i % 40 for i in range(200)], "label": ["q"] * 200})
    ids = pd.DataFrame({"user_id": range(1000, 1060), "age": range(60)})
    other = pd.DataFrame({"item_id": range(2000, 2060), "age2": range(60)})
    _ingest(env, env.b, ranks=ranks, counts=counts, ids=ids, other=other)
    assert call(env, "find_table_links", {"project_id": env.b.id})["links"] == []


def test_find_table_links_does_not_match_a_count_with_ids_that_start_at_one(env):
    customers = pd.DataFrame({"id": range(1, 1001), "city": ["a", "b"] * 500})
    orders = pd.DataFrame({"quantity": [i % 30 + 1 for i in range(400)], "label": ["q"] * 400})
    _ingest(env, env.b, customers=customers, orders=orders)
    assert call(env, "find_table_links", {"project_id": env.b.id})["links"] == []


def test_find_table_links_does_not_match_a_few_small_ids_with_a_long_id_column(env):
    sales = pd.DataFrame(
        {"shop_id": [i % 50 for i in range(6000)], "item_id": [i % 2000 for i in range(6000)]}
    )
    items = pd.DataFrame(
        {"item_id": range(2000), "item_category_id": [i % 40 for i in range(2000)]}
    )
    shops = pd.DataFrame({"shop_id": range(50), "city": ["c"] * 50})
    categories = pd.DataFrame({"item_category_id": range(40), "name": [f"n{i}" for i in range(40)]})
    by_name = _ingest(env, env.b, sales=sales, items=items, shops=shops, categories=categories)
    found = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    real = {
        (by_name["sales"], by_name["items"], "item_id"),
        (by_name["sales"], by_name["shops"], "shop_id"),
        (by_name["items"], by_name["categories"], "item_category_id"),
    }
    # the shop ids lie inside the item ids, and the item ids inside nothing: not links
    assert {(*link["datasets"], link["column"]) for link in found} == real


def test_find_table_links_does_not_match_ids_with_a_row_number_by_their_values(env):
    sales = pd.DataFrame({"item_id": [i % 500 + 7 for i in range(3000)], "n": range(3000)})
    rows = pd.DataFrame({"ID": range(5000), "shop": ["s"] * 5000})
    _ingest(env, env.b, sales=sales, rows=rows)
    assert call(env, "find_table_links", {"project_id": env.b.id})["links"] == []


def test_find_table_links_matches_an_auto_increment_key_the_other_column_mostly_covers(env):
    customers = pd.DataFrame({"id": range(1, 1001), "age": [i % 60 + 18 for i in range(1000)]})
    orders = pd.DataFrame({"client_id": [i % 1000 + 1 for i in range(3000)], "n": range(3000)})
    by_name = _ingest(env, env.b, customers=customers, orders=orders)
    (link,) = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    assert link["datasets"] == [by_name["customers"], by_name["orders"]]
    assert link["columns"] == ["id", "client_id"] and link["basis"] == "values"


def test_find_table_links_puts_a_link_by_name_before_one_by_values(env):
    codes = [f"s{i:03d}" for i in range(120)]
    customers = pd.DataFrame({"cid": range(1, 121), "serial": codes})
    orders = pd.DataFrame(
        {"cid": [i % 120 + 61 for i in range(360)], "unit": [codes[i % 120] for i in range(360)]}
    )
    _ingest(env, env.b, customers=customers, orders=orders)
    links = call(env, "find_table_links", {"project_id": env.b.id})["links"]
    assert [link.get("basis") for link in links] == [None, "values"]
    assert links[0]["shared"] < links[1]["shared"] == 1.0


def test_find_table_links_says_what_it_did_not_examine(env, monkeypatch):
    frame = pd.DataFrame({"k": range(30), "v": range(30)})
    for i in range(3):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, f"d{i}", DatasetType.TRAIN, [frame])
    monkeypatch.setattr(builtin, "_LINK_DATASETS", 2)
    found = call(env, "find_table_links", {"project_id": env.b.id})
    assert found["n_datasets_not_examined"] == 2 and len(found["datasets"]) == 2  # b has 4
    monkeypatch.setattr(builtin, "_LINK_DATASETS", 8)
    monkeypatch.setattr(builtin, "_LINK_SECS", -1.0)
    found = call(env, "find_table_links", {"project_id": env.b.id})
    assert found["truncated"] is True and found["links"] == []


def test_find_table_links_ignores_constant_float_and_barely_shared_columns(env):
    one = pd.DataFrame({"k": range(40), "f": [0.5 * i for i in range(40)], "c": ["x"] * 40})
    two = pd.DataFrame({"k": range(30, 70), "f": [0.5 * i for i in range(40)], "c": ["x"] * 40})
    for name, frame in (("one", one), ("two", two)):
        ingest.ingest_batches(env.storage, env.conn, env.b.id, name, DatasetType.TRAIN, [frame])
    found = call(env, "find_table_links", {"project_id": env.b.id})
    assert found["links"] == []  # k shares 25% of its values, f is a float, c is constant


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


def _two_tables(env, project, other_rows=None):
    keys = pd.DataFrame({"Id": range(1, 41), "label": ["a", "b"] * 20})
    events = pd.DataFrame(
        {"id": [i % 40 + 1 for i in range(120)], "amount": range(120), "tag": ["t"] * 120}
    )
    if other_rows is not None:
        events = events.iloc[:other_rows]
    for name, frame in (("keys", keys), ("events", events)):
        ingest.ingest_batches(env.storage, env.conn, project.id, name, DatasetType.TRAIN, [frame])
    return {d.name: d for d in projects.list_datasets(env.conn, project.id)}


def test_propose_join_returns_the_parameters_of_a_join(env):
    by_name = _two_tables(env, env.a)
    args = {"dataset_id": by_name["keys"].id, "other_dataset_id": by_name["events"].id}
    found = call(env, "propose_join", {**args, "key": "Id", "other_key": "id", "notes": "why"})
    assert found["proposal"] is True and found["kind"] == "join" and found["rationale"] == "why"
    assert found["config"] == {
        "other_dataset_id": by_name["events"].id,
        "key": "Id",
        "other_key": "id",
        "summarize": False,
        "columns": [],
    }
    # the events repeat their key: asked for as they are, the join would be refused
    assert [w["code"] for w in found["warnings"]] == ["join_key_repeats"]
    found = call(
        env,
        "propose_join",
        {
            **args,
            "key": "Id",
            "other_key": "id",
            "summarize": True,
            "columns": "amount, tag,amount",
        },
    )
    assert found["config"]["columns"] == ["amount", "tag"] and found["warnings"] == []


def _shop(env):
    customers = pd.DataFrame({"id": range(1, 61), "churned": [0, 1, 0] * 20})
    orders = pd.DataFrame({"id": range(100, 220), "customer_id": [i % 60 + 1 for i in range(120)]})
    items = pd.DataFrame({"order_id": [100 + i % 120 for i in range(300)], "qty": range(300)})
    return _ingest(env, env.b, items=items, orders=orders, customers=customers)


def test_propose_first_join_starts_from_the_dataset_with_the_column_to_predict(env):
    by_name = _shop(env)
    found = call(env, "propose_first_join", {"project_id": env.b.id, "target": "Churned"})
    assert found["proposal"] is True and found["kind"] == "join"
    assert found["dataset_id"] == by_name["customers"]
    assert found["config"] == {
        "other_dataset_id": by_name["orders"],
        "key": "id",
        "other_key": "customer_id",
        "summarize": True,  # the orders repeat their customer
        "columns": [],
    }
    assert found["warnings"] == []
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call(
            env,
            "propose_first_join",
            {"project_id": env.b.id, "target": "x"},
            user=env.users.outsider,
        )


def test_propose_first_join_looks_up_the_one_row_per_key_side_of_a_fact_table(env):
    by_name = _shop(env)
    found = call(env, "propose_first_join", {"project_id": env.b.id, "target": "qty"})
    # the items hold the column to predict: the orders are looked up, not summarized into one row
    assert found["dataset_id"] == by_name["items"]
    assert found["config"]["other_dataset_id"] == by_name["orders"]
    assert found["config"]["key"] == "order_id" and found["config"]["other_key"] == "id"
    assert found["config"]["summarize"] is False and found["warnings"] == []


def test_propose_first_join_does_not_summarize_a_one_to_one_link(env):
    left = pd.DataFrame({"k": range(1, 61), "a": range(60)})
    right = pd.DataFrame({"k": range(1, 61), "b": range(60)})
    by_name = _ingest(env, env.b, left=left, right=right)
    found = call(env, "propose_first_join", {"project_id": env.b.id, "target": "b"})
    assert found["dataset_id"] == by_name["right"]
    assert found["config"]["other_dataset_id"] == by_name["left"]
    assert found["config"]["summarize"] is False and found["config"]["other_key"] == ""


def test_propose_first_join_says_what_it_cannot_do(env):
    repeating = pd.DataFrame({"k": [i % 40 for i in range(120)], "a": range(120)})
    other = pd.DataFrame({"k": [i % 40 for i in range(160)], "b": range(160)})
    _ingest(env, env.b, repeating=repeating, other=other)
    with pytest.raises(ToolError, match="find_table_links"):
        call(env, "propose_first_join", {"project_id": env.b.id, "target": "a"})  # both repeat
    with pytest.raises(ToolError, match="ask the user which column"):
        call(env, "propose_first_join", {"project_id": env.b.id})
    with pytest.raises(ToolError, match="no dataset of the project has a column named"):
        call(env, "propose_first_join", {"project_id": env.b.id, "target": "nope"})


def test_propose_join_warns_about_few_matches_and_a_result_over_the_limit(env, monkeypatch):
    by_name = _two_tables(env, env.a)
    outside = pd.DataFrame({"Id": range(1000, 1040), "z": range(40)})
    ingest.ingest_batches(env.storage, env.conn, env.a.id, "outside", DatasetType.TRAIN, [outside])
    other = {d.name: d for d in projects.list_datasets(env.conn, env.a.id)}["outside"]
    found = call(
        env,
        "propose_join",
        {"dataset_id": by_name["keys"].id, "other_dataset_id": other.id, "key": "Id"},
    )
    assert [w["code"] for w in found["warnings"]] == ["join_few_matches"]
    assert found["warnings"][0]["params"] == {"share": "0"}
    monkeypatch.setattr(builtin, "MAX_OUTPUT_CELLS", 100)
    args = {"dataset_id": by_name["keys"].id, "other_dataset_id": by_name["events"].id}
    found = call(env, "propose_join", {**args, "key": "Id", "other_key": "id", "summarize": True})
    (warning,) = [w for w in found["warnings"] if w["code"] == "join_too_large"]
    assert warning["params"] == {"cells": "0", "limit": "0"}


def test_propose_join_does_not_judge_the_matching_keys_of_a_sample(env, monkeypatch):
    by_name = _two_tables(env, env.a)
    outside = pd.DataFrame({"Id": range(1000, 1040), "z": range(40)})
    ingest.ingest_batches(env.storage, env.conn, env.a.id, "outside", DatasetType.TRAIN, [outside])
    other = {d.name: d for d in projects.list_datasets(env.conn, env.a.id)}["outside"]
    args = {"dataset_id": by_name["keys"].id, "other_dataset_id": other.id, "key": "Id"}
    assert [w["code"] for w in call(env, "propose_join", args)["warnings"]] == ["join_few_matches"]
    monkeypatch.setattr(builtin, "_LINK_FULL_ROWS", 10)
    monkeypatch.setattr(builtin, "_LINK_SAMPLE_ROWS", 25)  # two samples share few keys
    assert call(env, "propose_join", args)["warnings"] == []


def test_propose_join_refuses_what_a_join_cannot_do(env):
    by_name = _two_tables(env, env.a)
    keys, events = by_name["keys"].id, by_name["events"].id
    with pytest.raises(ToolError, match="different projects"):
        call(
            env, "propose_join", {"dataset_id": keys, "other_dataset_id": env.ds_b.id, "key": "Id"}
        )
    with pytest.raises(ToolError, match="itself"):
        call(env, "propose_join", {"dataset_id": keys, "other_dataset_id": keys, "key": "Id"})
    with pytest.raises(ToolError, match="column not found in the other dataset"):
        call(env, "propose_join", {"dataset_id": keys, "other_dataset_id": events, "key": "Id"})
    args = {"dataset_id": keys, "other_dataset_id": events, "key": "Id", "other_key": "id"}
    with pytest.raises(ToolError, match="column not found in the other dataset"):
        call(env, "propose_join", {**args, "columns": "nope"})
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call(env, "propose_join", args, user=env.users.outsider)
    # a conversation of project B cannot reach project A
    with pytest.raises(ToolError, match=NOT_ALLOWED):
        call(env, "propose_join", args, project_id=env.b.id)

"""The MCP endpoint: off by default, a full-scope bearer token only, a browser's Origin
checked, and nothing but the registry's read-only tools behind it."""

import asyncio
import io
import json
import logging
from contextlib import closing

import pytest

from api_helpers import add_user, connect, iris_frame, login
from fione.assistant import store as assistant_store
from fione.auth import service as auth_service
from fione.auth.roles import Role
from fione.auth.tokens import TokenScope
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType
from fione.tools import list_tools
from fione.version import __version__

PROTOCOL = "2025-06-18"


def rpc(method, params=None, id=1):
    message = {"jsonrpc": "2.0", "id": id, "method": method}
    return message if params is None else {**message, "params": params}


@pytest.fixture
def mcp(make_client):
    client = make_client(mcp_enabled=True)
    user = add_user(client, "ed", Role.EDITOR)
    return client, user


def bearer(client, user, *, scope=TokenScope.FULL, revoke=False):
    with closing(connect(client)) as conn:
        record, token = auth_service.create_token(conn, user.id, "mcp", scope=scope)
        if revoke:
            auth_service.revoke_token(conn, record.id)
    return {"Authorization": f"Bearer {token}"}


def post(client, body, headers=None):
    return client.post("/mcp", json=body, headers=headers)


def call(client, headers, name, arguments=None):
    params = {"name": name} if arguments is None else {"name": name, "arguments": arguments}
    r = post(client, rpc("tools/call", params), headers)
    assert r.status_code == 200, r.text
    return r.json()["result"]


def iris_dataset(client, user):
    with closing(connect(client)) as conn:
        project = projects.create_project(conn, user, "P")
        stream = io.BytesIO(iris_frame().to_csv(index=False).encode())
        dataset = ingest_csv(
            client.app.state.storage, conn, project.id, "iris", DatasetType.TRAIN, stream
        )
    return project, dataset


def counts(client):
    with closing(connect(client)) as conn:
        return tuple(
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("jobs", "chat_proposals")
        )


def test_disabled_is_404(make_client):
    client = make_client()
    user = add_user(client, "ed", Role.EDITOR)
    assert post(client, rpc("ping"), bearer(client, user)).status_code == 404
    assert client.get("/mcp").status_code == 404


def test_auth(mcp):
    client, user = mcp
    r = post(client, rpc("ping"))
    assert (r.status_code, r.headers["www-authenticate"]) == (401, "Bearer")
    assert post(client, rpc("ping"), {"Authorization": "Bearer nope"}).status_code == 401
    assert post(client, rpc("ping"), bearer(client, user, revoke=True)).status_code == 401
    assert (
        post(client, rpc("ping"), bearer(client, user, scope=TokenScope.NOTEBOOK)).status_code
        == 403
    )
    login(client, "ed")  # a session cookie alone is not credentials
    assert post(client, rpc("ping")).status_code == 401
    assert post(client, rpc("ping"), bearer(client, user)).status_code == 200


@pytest.mark.parametrize(
    ("origin", "status"),
    [
        ("http://evil.example", 403),
        ("null", 403),
        ("http://localhost:5173", 200),
        ("http://127.0.0.1", 200),
        ("http://[::1]:3000", 200),
        ("https://fione.example.com", 200),
        (None, 200),
    ],
)
def test_origin(make_client, origin, status):
    client = make_client(mcp_enabled=True, public_url="https://fione.example.com")
    user = add_user(client, "ed", Role.EDITOR)
    headers = bearer(client, user) | ({} if origin is None else {"Origin": origin})
    assert post(client, rpc("ping"), headers).status_code == status


def test_initialize_negotiates(mcp):
    client, user = mcp
    headers = bearer(client, user)

    def initialize(version):
        r = post(client, rpc("initialize", {"protocolVersion": version}), headers)
        assert "mcp-session-id" not in r.headers
        return r.json()["result"]

    assert initialize("2025-06-18")["protocolVersion"] == "2025-06-18"
    result = initialize("2099-01-01")
    assert result["protocolVersion"] == "2025-11-25"
    assert result["serverInfo"] == {"name": "fione", "version": __version__}
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    r = post(client, rpc("ping"), headers | {"MCP-Protocol-Version": "1999-01-01"})
    assert r.status_code == 400
    r = post(client, rpc("ping"), headers | {"MCP-Protocol-Version": PROTOCOL})
    assert r.status_code == 200
    r = post(client, rpc("ping"), headers | {"Accept": "text/html"})
    assert r.status_code == 406


def test_notification_is_202_empty(mcp):
    client, user = mcp
    r = post(
        client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, bearer(client, user)
    )
    assert (r.status_code, r.content) == (202, b"")


def test_get_and_delete_are_405(mcp):
    client, user = mcp
    for method in ("GET", "DELETE"):
        r = client.request(method, "/mcp", headers=bearer(client, user))
        assert (r.status_code, r.headers["allow"]) == (405, "POST")


def test_batch_and_parse_errors(mcp):
    client, user = mcp
    headers = bearer(client, user)
    batch = post(client, [rpc("ping")], headers)
    assert batch.status_code == 400
    assert batch.json()["error"] == {"code": -32600, "message": "batching not supported"}
    broken = client.post("/mcp", content=b"{not json", headers=headers)
    assert (broken.status_code, broken.json()["error"]["code"]) == (400, -32700)
    for body in ({"id": 1, "method": "ping"}, "ping", {"jsonrpc": "2.0", "id": 1, "method": 7}):
        r = post(client, body, headers)
        assert (r.status_code, r.json()["error"]["code"]) == (400, -32600), body


def test_unknown_method_is_32601(mcp):
    client, user = mcp
    r = post(client, rpc("resources/list"), bearer(client, user))
    assert r.status_code == 200
    assert r.json()["error"]["code"] == -32601


def test_tools_list_matches_the_registry(mcp):
    client, user = mcp
    tools = post(client, rpc("tools/list"), bearer(client, user)).json()["result"]["tools"]
    assert [t["name"] for t in tools] == [t["function"]["name"] for t in list_tools()]
    assert all(t["annotations"]["readOnlyHint"] is True for t in tools)
    assert all(t["inputSchema"]["type"] == "object" for t in tools)


def test_call_reads_and_hides_samples(make_client, fake_llm):
    fake = fake_llm()
    client = make_client(mcp_enabled=True, llm_base_url=fake.url, llm_provider="openai")
    user = add_user(client, "ed", Role.EDITOR)
    _, dataset = iris_dataset(client, user)
    with closing(connect(client)) as conn:  # the chat's provider may be sent example values
        assistant_store.set_samples_allowed(conn, fake.url, True, user.id)
        assert assistant_store.samples_allowed(conn, fake.url)
    result = call(client, bearer(client, user), "describe_dataset", {"dataset_id": dataset.id})
    assert result["isError"] is False
    assert "_data_notice" in result["structuredContent"]
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    assert "top_values_hidden" in result["content"][0]["text"]


def test_call_other_users_dataset_is_not_allowed(mcp):
    client, user = mcp
    _, dataset = iris_dataset(client, user)
    other = add_user(client, "st", Role.EDITOR)
    result = call(client, bearer(client, other), "describe_dataset", {"dataset_id": dataset.id})
    assert result["isError"] is True
    assert "not found or not allowed" in result["content"][0]["text"]


def test_no_way_to_write(mcp):
    client, user = mcp
    _, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    before = counts(client)
    refused = call(
        client, headers, "start_training", {"dataset_id": dataset.id, "target": "species"}
    )
    assert (refused["isError"], refused["content"][0]["text"]) == (True, "unknown tool")
    proposed = call(
        client, headers, "propose_training_config", {"dataset_id": dataset.id, "target": "species"}
    )
    assert proposed["structuredContent"]["proposal"] is True
    assert counts(client) == before  # nothing is stored, and no job started


def test_bad_call_params_are_32602(mcp):
    client, user = mcp
    r = post(
        client,
        rpc("tools/call", {"name": "describe_dataset", "arguments": []}),
        bearer(client, user),
    )
    assert r.json()["error"]["code"] == -32602


def test_mcp_is_not_in_openapi(mcp):
    client, _ = mcp
    assert "/mcp" not in client.app.openapi()["paths"]


def test_token_not_logged_and_calls_say_via_mcp(mcp, caplog):
    client, user = mcp
    _, dataset = iris_dataset(client, user)
    headers = bearer(client, user)
    token = headers["Authorization"].split()[1]
    with caplog.at_level(logging.DEBUG):
        call(client, headers, "describe_dataset", {"dataset_id": dataset.id})
        post(client, rpc("ping"), {"Authorization": "Bearer wrong-token-value"})
    assert token not in caplog.text and "wrong-token-value" not in caplog.text
    assert "via=mcp" in caplog.text


def test_nan_and_odd_ids_and_deep_nesting_are_refused_not_500(mcp):
    client, user = mcp
    headers = bearer(client, user)
    for raw in (
        b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}',
        b'{"jsonrpc":"2.0","id":Infinity,"method":"ping"}',
        b"[" * 100_000 + b"]" * 100_000,
    ):
        r = client.post("/mcp", content=raw, headers=headers)
        assert (r.status_code, r.json()["error"]["code"]) == (400, -32700), raw[:40]
    for odd in (True, None, [1], {"a": 1}, 1.5):
        r = post(client, {"jsonrpc": "2.0", "id": odd, "method": "ping"}, headers)
        assert r.status_code in (202, 400) and r.status_code != 500, odd
    assert post(client, rpc("ping", id="abc"), headers).json()["id"] == "abc"


def test_a_call_waits_for_a_slot_and_then_says_busy(mcp, monkeypatch):
    client, user = mcp
    monkeypatch.setattr("fione.mcp.BUSY_WAIT_SECS", 0.05)
    client.app.state.mcp_slots = asyncio.Semaphore(0)  # both slots taken
    r = post(client, rpc("tools/call", {"name": "list_projects"}, id=7), bearer(client, user))
    assert (r.status_code, r.json()["error"]) == (200, {"code": -32000, "message": "busy"})
    assert r.json()["id"] == 7


def test_the_log_line_names_a_bounded_number_of_arguments(mcp, caplog):
    client, user = mcp
    many = {f"k{i}": i for i in range(5000)}
    with caplog.at_level(logging.INFO, logger="fione.tools"):
        call(client, bearer(client, user), "list_projects", many)
    (line,) = [r.getMessage() for r in caplog.records if r.name == "fione.tools"]
    assert len(line) < 2000

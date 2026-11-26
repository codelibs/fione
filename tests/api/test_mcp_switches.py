"""MCP is on by default, with its tools that change things; an administrator switches either
off (and on again) on the System page, within what the server's settings allow."""

import pytest
from test_mcp import bearer, post, rpc
from test_uploads_api import datasets, make_token, new_project, put

from api_helpers import add_user, login
from fione.auth.roles import Role
from fione.config import Settings

WRITE_TOOL = "start_training"


def tools(client, headers) -> set[str] | int:
    r = post(client, rpc("tools/list"), headers)
    return (
        r.status_code if r.status_code != 200 else {t["name"] for t in r.json()["result"]["tools"]}
    )


def switch(client, csrf, name, enabled):
    data = {"csrf_token": csrf, "name": name, "enabled": "true" if enabled else "false"}
    return client.post("/admin/system/mcp", data=data, follow_redirects=False)


@pytest.fixture
def world(make_client):
    """The defaults (both on), an editor's token and project, and an administrator's form."""
    client = make_client(mcp_enabled=True, mcp_write_enabled=True)
    user, project_id = new_project(client)
    headers = bearer(client, user)
    add_user(client, "admin", Role.ADMIN)
    csrf = login(client, "admin")
    return client, user, project_id, headers, csrf


def test_mcp_and_its_write_tools_are_on_by_default(tmp_path, monkeypatch):
    for name in ("FIONE_MCP_ENABLED", "FIONE_MCP_WRITE_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(data_dir=tmp_path)
    assert settings.mcp_enabled and settings.mcp_write_enabled


def test_switching_mcp_off_stops_it_at_once(world):
    client, _, _, headers, csrf = world
    assert WRITE_TOOL in tools(client, headers)
    r = switch(client, csrf, "mcp", False)
    assert (r.status_code, r.headers["location"]) == (303, "/admin/system#mcp-title")
    assert tools(client, headers) == 404
    page = client.get("/admin/system").text
    assert 'data-switch="mcp">Off' in page and 'data-switch="mcp_write">Off' in page
    switch(client, csrf, "mcp", True)
    assert WRITE_TOOL in tools(client, headers)


def test_switching_the_write_tools_off_hides_them_and_stops_upload_urls(world):
    client, user, project_id, headers, csrf = world
    token = make_token(client, user, project_id)
    switch(client, csrf, "mcp_write", False)
    listed = tools(client, headers)
    assert "list_projects" in listed and WRITE_TOOL not in listed
    assert put(client, token).status_code == 404  # an outstanding URL too, and not used up
    assert datasets(client, project_id) == []
    switch(client, csrf, "mcp_write", True)
    assert put(client, token).status_code == 201


@pytest.mark.parametrize(
    ("settings", "locked"),
    [
        ({"mcp_enabled": False, "mcp_write_enabled": True}, "FIONE_MCP_ENABLED"),
        ({"mcp_enabled": True, "mcp_write_enabled": False}, "FIONE_MCP_WRITE_ENABLED"),
    ],
)
def test_a_setting_of_false_is_never_widened(make_client, settings, locked):
    client = make_client(**settings)
    user, _ = new_project(client)
    headers = bearer(client, user)
    add_user(client, "admin", Role.ADMIN)
    csrf = login(client, "admin")
    for name in ("mcp", "mcp_write"):
        switch(client, csrf, name, True)
    if settings["mcp_enabled"]:
        assert WRITE_TOOL not in tools(client, headers)
    else:
        assert tools(client, headers) == 404
    page = client.get("/admin/system").text
    assert f"{locked}=false" in page


def test_only_an_administrator_switches(world):
    client, _, _, headers, _ = world
    csrf = login(client, "ed")
    assert switch(client, csrf, "mcp", False).status_code == 403
    assert WRITE_TOOL in tools(client, headers)
    admin = login(client, "admin")
    bad = {"csrf_token": admin, "name": "llm", "enabled": "false"}
    assert client.post("/admin/system/mcp", data=bad).status_code == 422
    assert switch(client, "not-the-token", "mcp", False).status_code in (401, 403)
    assert WRITE_TOOL in tools(client, headers)


def test_the_system_page_names_the_endpoint(world):
    client = world[0]
    page = client.get("/admin/system").text
    assert "http://testserver/mcp" in page and 'action="/admin/system/mcp"' in page

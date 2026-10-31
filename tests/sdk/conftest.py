import pytest
from fione_sdk import Client

from api_helpers import add_user, bearer, connect
from fione.auth import service as auth
from fione.auth.tokens import TokenScope


@pytest.fixture
def api(make_client):
    """The in-process API the SDK talks to."""
    return make_client()


@pytest.fixture
def sdk(api):
    """A ``Client`` for an editor, wired to the in-process API."""
    token = bearer(api, add_user(api, "editor").id)["Authorization"].removeprefix("Bearer ")
    return Client(token=token, http=api)


@pytest.fixture
def notebook_sdk(api):
    """A ``Client`` with a notebook-scope token, as a notebook gets it."""
    user = add_user(api, "nbuser")
    conn = connect(api)
    try:
        _, token = auth.create_token(
            conn, user.id, "nb", scope=TokenScope.NOTEBOOK, expires_at=auth.expiry_after(3600)
        )
    finally:
        conn.close()
    return Client(token=token, http=api)

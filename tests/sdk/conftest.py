import pytest
from fione_sdk import Client

from api_helpers import add_user, bearer


@pytest.fixture
def api(make_client):
    """The in-process API the SDK talks to."""
    return make_client()


@pytest.fixture
def sdk(api):
    """A ``Client`` for an editor, wired to the in-process API."""
    token = bearer(api, add_user(api, "editor").id)["Authorization"].removeprefix("Bearer ")
    return Client(token=token, http=api)

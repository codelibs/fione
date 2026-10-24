import warnings
from contextlib import ExitStack

import pytest

with warnings.catch_warnings():
    # Starlette prefers httpx2 for its TestClient; httpx is what the lockfile has and works.
    # The warning is raised once, at import: importing here, before any test module, keeps
    # the API tests clean under -W error.
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    from fastapi.testclient import TestClient

from api_helpers import make_settings  # noqa: E402

from fione.api.app import create_app  # noqa: E402


@pytest.fixture
def make_client(tmp_path):
    """``make_client(data_dir=None, *, raise_server_exceptions=True, **settings)``: a started
    TestClient (its lifespan has run) on a fresh app with the runner off; closed at teardown."""
    with ExitStack() as stack:

        def factory(data_dir=None, *, raise_server_exceptions=True, **overrides):
            settings = make_settings(data_dir or tmp_path / "data", **overrides)
            app = create_app(settings, start_runner=False)
            client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
            return stack.enter_context(client)

        yield factory


@pytest.fixture
def client(make_client):
    return make_client()

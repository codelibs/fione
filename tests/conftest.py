import os
import warnings
import zlib
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
from fione.engine import automl  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """``FIONE_TEST_SHARD=2/3`` runs the second of three slices of the suite, so CI can spread
    it over several machines. A test lands in a slice by a hash of its id (of its ``xdist_group``
    name if it has one, so that the tests sharing a group stay together): the slices are about
    the same size, and the same test always lands in the same one."""
    shard = os.environ.get("FIONE_TEST_SHARD")
    if not shard:
        return
    index, count = (int(part) for part in shard.split("/"))
    assert 1 <= index <= count, f"FIONE_TEST_SHARD must be i/n with 1 <= i <= n, not {shard}"
    kept, dropped = [], []
    for item in items:
        group = item.get_closest_marker("xdist_group")
        key = group.args[0] if group else item.nodeid
        in_shard = zlib.crc32(key.encode()) % count == index - 1
        (kept if in_shard else dropped).append(item)
    items[:] = kept
    config.hook.pytest_deselected(items=dropped)


@pytest.fixture(autouse=True)
def _no_explain_after_training(monkeypatch):
    """Training does not queue an explain job in tests unless a test asks for it."""
    monkeypatch.setenv("FIONE_EXPLAIN_AFTER_TRAINING", "false")


@pytest.fixture
def extra_seeds():
    """Ask for this to train with the extra seeds of the default configuration."""


@pytest.fixture(autouse=True)
def _no_extra_seeds(request, monkeypatch):
    """Extra seeds make every training slower and the suite runs training in parallel, so only
    the tests that ask for ``extra_seeds`` (and the timing tests) train with them."""
    if "extra_seeds" not in request.fixturenames and not request.node.get_closest_marker("timing"):
        monkeypatch.setattr(automl, "BAG_EXTRA", 0)


def _kill_workers(app) -> None:
    if app.state.runner is not None:
        app.state.runner.shutdown(kill_running=True)


@pytest.fixture
def make_client(tmp_path):
    """``make_client(data_dir=None, *, raise_server_exceptions=True, start_runner=False,
    **settings)``: a started TestClient (its lifespan has run) on a fresh app, with the job
    runner off unless asked for; closed at teardown, when running workers are killed too."""
    with ExitStack() as stack:

        def factory(
            data_dir=None, *, raise_server_exceptions=True, start_runner=False, **overrides
        ):
            settings = make_settings(data_dir or tmp_path / "data", **overrides)
            app = create_app(settings, start_runner=start_runner)
            if start_runner:
                # Registered before the client: runs after the lifespan has stopped the runner.
                stack.callback(_kill_workers, app)
            client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
            return stack.enter_context(client)

        yield factory


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def fake_llm():
    """``fake_llm(script=None, **kwargs)``: a started ``FakeLlm``, stopped at teardown."""
    from fake_llm import FakeLlm

    started = []

    def factory(script=None, **kwargs):
        fake = FakeLlm(script, **kwargs).start()
        started.append(fake)
        return fake

    yield factory
    for fake in started:
        fake.stop()

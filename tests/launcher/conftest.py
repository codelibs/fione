import threading

import pytest

from fione_launcher.server import Launcher, make_server
from launcher_helpers import NETWORK, PROJECT, Api, FakeDocker, make_config


@pytest.fixture
def docker():
    return FakeDocker()


@pytest.fixture
def launcher(docker):
    return Launcher(make_config(), docker, project=PROJECT, network=NETWORK)


@pytest.fixture
def api(launcher):
    server = make_server(launcher, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True)
    thread.start()
    try:
        yield Api(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)

"""The launcher's configuration, read from the environment once at start."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from fione_launcher.spec import ORIGIN

_MIN_SECRET = 32
_IMAGE = re.compile(r"\S+")
_COUNT = re.compile(r"[1-9][0-9]{0,3}")


def _exit(message: str) -> SystemExit:
    return SystemExit(f"fione_launcher: {message}")  # exit status 1; never echo a value


@dataclass(frozen=True)
class LauncherConfig:
    secret: str = field(repr=False)
    image: str
    api_url: str
    max_running: int
    socket_path: str = "/var/run/docker.sock"
    port: int = 8000

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "LauncherConfig":
        secret = env.get("FIONE_LAUNCHER_SECRET", "")
        if len(secret) < _MIN_SECRET:
            raise _exit(f"FIONE_LAUNCHER_SECRET must be at least {_MIN_SECRET} characters")
        image = env.get("FIONE_NOTEBOOK_IMAGE", "")
        if not _IMAGE.fullmatch(image):
            raise _exit("FIONE_NOTEBOOK_IMAGE is missing or malformed")
        api_url = env.get("FIONE_NOTEBOOK_API_URL", "http://notebook-gateway:8081")
        if not ORIGIN.fullmatch(api_url):
            raise _exit("FIONE_NOTEBOOK_API_URL must be scheme://host[:port]")
        max_running = env.get("FIONE_NOTEBOOK_MAX_RUNNING", "4")
        if not _COUNT.fullmatch(max_running):
            raise _exit("FIONE_NOTEBOOK_MAX_RUNNING must be a whole number from 1")
        return cls(secret=secret, image=image, api_url=api_url, max_running=int(max_running))

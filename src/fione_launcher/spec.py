"""The start request and the fixed container spec. Only the uid and the request's fixed-format
values reach the create body; everything else is constant or from the launcher's
configuration."""

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fione_launcher.config import LauncherConfig

_UID = re.compile(r"[1-9][0-9]{0,17}")  # as Fione writes it: no sign, no leading zero
_HEX_32_BYTES = re.compile(r"[0-9a-f]{64}")
_TOKEN = re.compile(r"fione_[A-Za-z0-9_-]{20,100}")
ORIGIN = re.compile(r"https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?")
# A container lives at most this long (seconds), like its token and its Jupyter cookie.
MAX_LIFETIME = 604800
_FIELDS = {"launch_key", "cookie_secret", "token", "fione_origin", "expires_at"}

CPUS = 2
MEMORY = 4 * 1024**3  # and no swap
PIDS = 512
USER = "1000:1000"  # the notebook image's user
WORK_DIR = "/home/nb/work"


class InvalidRequest(ValueError):
    """A start request that does not match the fixed formats (never says which value)."""


def valid_uid(uid: str) -> bool:
    return _UID.fullmatch(uid) is not None


def container_name(project: str, uid: str) -> str:
    return f"{project}-nb-{uid}"


def volume_name(project: str, uid: str) -> str:
    return f"{project}-nb-home-{uid}"


def _text(data: dict, name: str, pattern: re.Pattern) -> str:
    value = data[name]
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise InvalidRequest(name)
    return value


@dataclass(frozen=True)
class StartRequest:
    launch_key: str = field(repr=False)
    cookie_secret: str = field(repr=False)
    token: str = field(repr=False)
    fione_origin: str
    expires_at: int

    @classmethod
    def parse(cls, data: object, *, now: float) -> "StartRequest":
        """The request from a decoded JSON body; ``InvalidRequest`` unless it has exactly the
        fields, each in its fixed format, and expires within ``MAX_LIFETIME`` from ``now``."""
        if not isinstance(data, dict) or set(data) != _FIELDS:
            raise InvalidRequest("fields")
        expires_at = data["expires_at"]
        if type(expires_at) is not int or not now < expires_at <= now + MAX_LIFETIME:
            raise InvalidRequest("expires_at")
        return cls(
            launch_key=_text(data, "launch_key", _HEX_32_BYTES),
            cookie_secret=_text(data, "cookie_secret", _HEX_32_BYTES),
            token=_text(data, "token", _TOKEN),
            fione_origin=_text(data, "fione_origin", ORIGIN),
            expires_at=expires_at,
        )


def container_body(
    cfg: "LauncherConfig", *, project: str, network: str, uid: str, req: StartRequest
) -> dict:
    """The Docker create body of ``uid``'s notebook container (named ``container_name``)."""
    return {
        "Image": cfg.image,
        "User": USER,
        "Env": [
            f"FIONE_NB_OWNER={uid}",
            f"FIONE_NB_KEY={req.launch_key}",
            f"FIONE_NB_COOKIE_SECRET={req.cookie_secret}",
            f"FIONE_NB_ORIGIN={req.fione_origin}",
            f"FIONE_NB_EXPIRES={req.expires_at}",
            f"FIONE_URL={cfg.api_url}",
            f"FIONE_TOKEN={req.token}",
        ],
        "Labels": {
            "fione.notebook": "1",
            "fione.project": project,
            "fione.uid": uid,
            "fione.expires": str(req.expires_at),
        },
        "HostConfig": {
            "NanoCpus": CPUS * 1_000_000_000,
            "Memory": MEMORY,
            "MemorySwap": MEMORY,
            "PidsLimit": PIDS,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "AutoRemove": True,
            "Init": True,
            "NetworkMode": network,
            "Mounts": [
                {"Type": "volume", "Source": volume_name(project, uid), "Target": WORK_DIR},
            ],
        },
        # The alias is what the gateway resolves, and only on this network.
        "NetworkingConfig": {"EndpointsConfig": {network: {"Aliases": [f"nb-{uid}"]}}},
    }

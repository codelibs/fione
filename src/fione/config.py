import ipaddress
import json
import os
import re
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_SETUP_TOKEN_LENGTH = 16
# The room a request needs besides the reply: the assistant's tools and longest system prompt
# take about 2,940 tokens (at 2 bytes per token), and a short question the rest.
MIN_PROMPT_TOKENS = 3008
_VISIBLE_ASCII = re.compile(r"[\x21-\x7e]+")  # it travels in an HTTP header
# scheme://host[:port] with dot-separated labels: what Fione's own origin must look like.
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_ORIGIN = re.compile(
    rf"(?P<scheme>https?)://(?P<host>{_LABEL}(?:\.{_LABEL})*)(?::(?P<port>[0-9]{{1,5}}))?"
)
_DEFAULT_PORTS = {"http": 80, "https": 443}
# scheme://host[:port] and an optional path, no credentials, query or fragment. The host is a
# name (Compose service names may have underscores), an IPv4 address or a bracketed IPv6 one.
_LLM_LABEL = r"[A-Za-z0-9_](?:[A-Za-z0-9_-]*[A-Za-z0-9_])?"
_LLM_URL = re.compile(
    rf"(?P<origin>https?://(?:{_LLM_LABEL}(?:\.{_LLM_LABEL})*|\[(?P<v6>[0-9A-Fa-f:.]+)\])"
    r"(?::(?P<port>[0-9]{1,5}))?)"
    r"(?P<path>(?:/[A-Za-z0-9._~%!$&'()*+,;=:@-]*)*)"
)
_LLM_MODEL = re.compile(r"[\x21-\x7e]{1,200}")
# The request body is Fione's; the extra body only adds to it.
LLM_RESERVED_KEYS = ("model", "messages", "tools", "stream", "stream_options", "max_tokens")


class Settings(BaseSettings):
    # A validation error would otherwise quote the input, secrets included.
    model_config = SettingsConfigDict(env_prefix="FIONE_", hide_input_in_errors=True)

    data_dir: Path = Path("/data")
    # Defaults below are derived from data_dir when left unset.
    storage_url: str = ""
    secret_key_path: Path | None = None
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    max_concurrent_train_jobs: int = 1
    max_concurrent_short_jobs: int = 4
    image_tag: str = "dev"
    serving_image: str = "ghcr.io/codelibs/fione-serving"
    # Queue an explain job (importance and partial dependence) after each training.
    explain_after_training: bool = True
    # REST API
    runner_enabled: bool = True
    cookie_secure: bool = False
    session_max_age_secs: int = 7 * 24 * 3600
    login_max_failures: int = Field(5, ge=1)  # per (client address, username) and window
    login_window_secs: int = 15 * 60
    # Per client address and window, whatever the usernames. Users sharing an address (NAT, or
    # a proxy while trust_proxy is off) share this budget: one client's wrong attempts can
    # block login for all of them. Behind a reverse proxy, set trust_proxy.
    login_max_failures_per_ip: int = Field(50, ge=1)
    # Trust X-Forwarded-For/-Host (the last value, the one the nearest proxy added): only behind
    # a reverse proxy that sets them; otherwise clients could choose their own address.
    trust_proxy: bool = False
    max_upload_bytes: int = 2**30
    # First-admin setup token; when unset, one is generated into <data_dir>/setup-token.
    setup_token: str | None = None
    # Fione's origin as browsers reach it (behind a TLS proxy Fione cannot know its scheme):
    # the MCP endpoint accepts browser requests from it.
    public_url: str | None = None
    # LLM assistant (off unless llm_base_url is set): an OpenAI-compatible server, or Ollama.
    llm_base_url: str | None = None
    llm_provider: Literal["openai", "ollama"] = "openai"
    llm_api_key: SecretStr | None = None
    # MLX models need a host-native Ollama on Apple Silicon; elsewhere use gemma4:12b.
    llm_model: str = "gemma4:12b-mlx"
    # Merged into every request; unset: no thinking output for ollama, nothing for openai.
    llm_extra_body: Annotated[dict | None, NoDecode] = None
    # ollama: pull the model when the server lacks it. Off: a host Ollama is the user's;
    # an administrator pulls on the system page.
    llm_auto_pull: bool = False
    # The read-only tools over MCP at /mcp, for an API token; off unless set.
    mcp_enabled: bool = False
    llm_max_tokens: int = Field(1024, ge=64, le=8192)  # per completion
    llm_context_tokens: int = Field(16384, le=262144)  # the budget of one request
    llm_max_tool_rounds: int = Field(6, ge=1, le=20)  # completions with tool calls per turn
    llm_turn_timeout_secs: int = Field(180, ge=10, le=1800)  # one turn, all its rounds
    llm_max_concurrent_turns: int = Field(2, ge=1, le=16)

    @field_validator("llm_extra_body", mode="before")
    @classmethod
    def _parse_extra_body(cls, value):
        if not isinstance(value, str):
            return value
        if not value.strip():
            return None
        try:
            return json.loads(value)
        except ValueError:
            raise ValueError("FIONE_LLM_EXTRA_BODY must be a JSON object") from None

    @model_validator(mode="after")
    def _derive_defaults(self) -> "Settings":
        if not self.setup_token:
            self.setup_token = None
        elif len(self.setup_token) < MIN_SETUP_TOKEN_LENGTH:
            raise ValueError(
                f"FIONE_SETUP_TOKEN must be at least {MIN_SETUP_TOKEN_LENGTH} characters"
            )
        if not self.storage_url:
            self.storage_url = (self.data_dir / "objects").as_uri()
        if self.secret_key_path is None:
            self.secret_key_path = self.data_dir / "secret.key"
        self._check_public_url()
        self._check_llm()
        return self

    def _check_public_url(self) -> None:
        """An empty value is unset; a set one is a bare origin, kept in its normal form."""
        if not self.public_url:
            self.public_url = None
        else:
            self.public_url = _normal_origin("public_url", self.public_url)

    def _check_llm(self) -> None:
        """Empty values are unset; the base URL is kept without a trailing slash, and the
        extra body defaults to what turns thinking off."""
        if self.llm_api_key is not None and not self.llm_api_key.get_secret_value():
            self.llm_api_key = None
        if self.llm_api_key is not None and not _VISIBLE_ASCII.fullmatch(
            self.llm_api_key.get_secret_value()
        ):
            raise ValueError("FIONE_LLM_API_KEY must be visible ASCII characters")
        if not _LLM_MODEL.fullmatch(self.llm_model):
            raise ValueError("FIONE_LLM_MODEL must be 1 to 200 visible ASCII characters")
        if self.llm_context_tokens - self.llm_max_tokens < MIN_PROMPT_TOKENS:
            raise ValueError(
                "FIONE_LLM_CONTEXT_TOKENS less FIONE_LLM_MAX_TOKENS must be at least"
                f" {MIN_PROMPT_TOKENS}, the room the assistant's tools and instructions need."
                " Even 4096, Ollama's default context, is too small for the tools: use"
                " FIONE_LLM_CONTEXT_TOKENS=16384, and set OLLAMA_CONTEXT_LENGTH=16384 on the"
                " Ollama server (Compose's ollama profile does; set it for an Ollama on the host)"
            )
        if self.llm_extra_body is None:
            self.llm_extra_body = (
                {"reasoning_effort": "none"} if self.llm_provider == "ollama" else {}
            )
        reserved = sorted(set(self.llm_extra_body) & set(LLM_RESERVED_KEYS))
        if reserved:
            raise ValueError(f"FIONE_LLM_EXTRA_BODY must not set {', '.join(reserved)}")
        if not self.llm_base_url:
            self.llm_base_url = None
            return
        match = _match_llm_url(self.llm_base_url)
        if match is None:
            raise ValueError(
                "FIONE_LLM_BASE_URL must be http(s)://host[:port][/path], no credentials,"
                " query or fragment"
            )
        self.llm_base_url = (match["origin"] + match["path"]).rstrip("/")
        if self.llm_provider == "ollama" and not match["path"].rstrip("/").endswith("/v1"):
            raise ValueError("FIONE_LLM_BASE_URL must end in /v1 with FIONE_LLM_PROVIDER=ollama")


def _match_llm_url(value: str) -> re.Match | None:
    """``value`` matched as an LLM base URL, or None if it is not one."""
    match = _LLM_URL.fullmatch(value)
    if match is None or (match["port"] and not 0 < int(match["port"]) <= 65535):
        return None
    if match["v6"]:
        try:
            ipaddress.IPv6Address(match["v6"])
        except ValueError:
            return None
    return match


def _normal_origin(name: str, value: str) -> str:
    """``value`` as browsers compare origins: the host in lower case, no default port."""
    match = _ORIGIN.fullmatch(value)
    if match is None or (match["port"] and int(match["port"]) > 65535):
        raise ValueError(f"FIONE_{name.upper()} must be scheme://host[:port], no path")
    scheme, host = match["scheme"], match["host"].lower()
    port = int(match["port"]) if match["port"] else _DEFAULT_PORTS[scheme]
    return f"{scheme}://{host}" + ("" if port == _DEFAULT_PORTS[scheme] else f":{port}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SECRET_LENGTH = 32


def load_secret(settings: Settings) -> bytes:
    """Return the server secret, creating a random 32-byte key file (mode 0600) if missing.

    The key file is published atomically (see ``create_private_file``). An existing file of
    any other length is rejected, never regenerated.
    """
    path = settings.secret_key_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _create_secret(path)
    data = path.read_bytes()
    if len(data) != SECRET_LENGTH:
        raise RuntimeError("secret key file is corrupt")
    return data


def _create_secret(path: Path) -> None:
    create_private_file(path, os.urandom(SECRET_LENGTH))


def create_private_file(path: Path, data: bytes) -> bool:
    """Publish ``data`` at ``path`` (mode 0600) unless the file exists; True if this call did.

    The data goes to a private temp file first and is published with ``os.link``, so the
    file is never visible empty or partial, even across processes or crashes.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            return False  # another process published first; its file is read by the caller
        return True
    finally:
        tmp.unlink(missing_ok=True)

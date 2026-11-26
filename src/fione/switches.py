"""The administrator's MCP switches on the System page, kept in the database. A switch only
narrows what the server's settings allow (``FIONE_MCP_ENABLED``, ``FIONE_MCP_WRITE_ENABLED``):
a setting of ``false`` keeps MCP, or its tools that change things, off whatever is stored.
Without a stored value a switch is on."""

import sqlite3
import time
from dataclasses import dataclass
from typing import Literal

from fione import db
from fione.config import Settings

Switch = Literal["mcp", "mcp_write"]


@dataclass(frozen=True)
class McpSwitches:
    allowed: bool  # FIONE_MCP_ENABLED
    writes_allowed: bool  # FIONE_MCP_WRITE_ENABLED
    stored: bool  # the administrator's switch of MCP
    stored_writes: bool  # and of its tools that change things

    @property
    def enabled(self) -> bool:
        """Whether ``/mcp`` answers."""
        return self.allowed and self.stored

    @property
    def writes(self) -> bool:
        """Whether MCP clients get the tools that change things (and upload URLs work)."""
        return self.enabled and self.writes_allowed and self.stored_writes


def mcp_switches(conn: sqlite3.Connection, settings: Settings) -> McpSwitches:
    stored = dict(conn.execute("SELECT name, enabled FROM switches").fetchall())
    return McpSwitches(
        allowed=settings.mcp_enabled,
        writes_allowed=settings.mcp_write_enabled,
        stored=bool(stored.get("mcp", 1)),
        stored_writes=bool(stored.get("mcp_write", 1)),
    )


def set_switch(conn: sqlite3.Connection, name: Switch, enabled: bool, user_id: int) -> None:
    with db.immediate(conn):
        conn.execute(
            "INSERT INTO switches (name, enabled, changed_by, changed_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (name) DO UPDATE SET enabled = excluded.enabled,"
            " changed_by = excluded.changed_by, changed_at = excluded.changed_at",
            (name, int(enabled), user_id, time.time()),
        )

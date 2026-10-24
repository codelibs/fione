"""Job handlers for test_jobs.py; workers import this via FIONE_JOB_HANDLER_MODULES."""

import subprocess
import time
from pathlib import Path

from fione.engine.events import Event
from fione.jobs.handlers import JobContext, register_handler


def _sleep(ctx: JobContext, seconds: float, *, check: bool = True) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check and ctx.should_stop():
            return
        time.sleep(0.05)


@register_handler("echo")
def echo(ctx: JobContext) -> None:
    for i, text in enumerate(["one", "two", "日本語 ✓"]):
        ctx.emit(Event("notice", data={"message": text, "i": i}))
    ctx.set_result({"ok": True})


@register_handler("sleep")
def sleep(ctx: JobContext) -> None:
    ctx.emit(Event("started"))
    _sleep(ctx, ctx.job.payload.get("seconds", 60))


@register_handler("automl")
def automl(ctx: JobContext) -> None:
    _sleep(ctx, ctx.job.payload.get("seconds", 1.0))


@register_handler("ignore_stop")
def ignore_stop(ctx: JobContext) -> None:
    ctx.emit(Event("started"))
    _sleep(ctx, ctx.job.payload.get("seconds", 300), check=False)


@register_handler("spawn_child")
def spawn_child(ctx: JobContext) -> None:
    child = subprocess.Popen(["sleep", "300"])
    ctx.emit(Event("started", data={"child_pid": child.pid}))
    _sleep(ctx, 300, check=ctx.job.payload.get("cooperative", False))


@register_handler("crash")
def crash(ctx: JobContext) -> None:
    raise RuntimeError("boom")


@register_handler("emit_flood")
def emit_flood(ctx: JobContext) -> None:
    for i in range(ctx.job.payload["n"]):
        ctx.emit(Event("trial", data={"i": i}))


@register_handler("abort_probe")
def abort_probe(ctx: JobContext) -> None:
    go = Path(ctx.job.payload["go_file"])
    deadline = time.monotonic() + 20
    while not go.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    try:
        ctx.emit(Event("notice", data={"message": "probe"}))
    except Exception:
        pass  # what the engine's per-family recovery does; JobAbort must get through
    ctx.set_result({"degraded": True})

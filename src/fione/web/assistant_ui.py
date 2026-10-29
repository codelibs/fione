"""The Fione-kun chat page: a project's conversations of the signed-in user, the thread of one
and the question form.

Conversations are their creator's alone, so every conversation id goes through
``store.get_conversation`` (404 for anyone else's, admins included) before anything is done
with it. Messages are escaped plain text; a tool row only names what was read. While a turn
is active, HTMX polls the thread; its last answer (and any failure to show it) is 286, which
ends the polling. The page never fails because the LLM cannot be used: it says why.
"""

import logging
from dataclasses import dataclass

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from fione import db, i18n
from fione.api.deps import Conn
from fione.assistant import store
from fione.assistant.store import (
    Conversation,
    ConversationNotFound,
    LimitReached,
    ProposalNotFound,
    TurnBusy,
)
from fione.assistant.turns import ERROR_CODES, LlmUnavailable, TooManyTurns
from fione.engine.config import TargetError, TrainConfig
from fione.models import service as models
from fione.modules.registry import redact
from fione.projects import service as projects
from fione.projects.service import DatasetNotFound, DatasetType, ProjectNotFound
from fione.schema import clean_text
from fione.tools import list_tools
from fione.web.access import (
    Ctx,
    SmallForm,
    action,
    dataset_in,
    field,
    model_in,
    page,
    parse_id,
    same_site,
)
from fione.web.easyml import STOP_POLLING
from fione.web.views import UiError, language, render

log = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)

ACTIVE = ("queued", "running")


@dataclass(frozen=True)
class Line:
    """One message as the thread shows it."""

    kind: str  # "user", "assistant" or "tool"
    text: str  # escaped by the template; for a tool row, its label's key
    state: str
    error_key: str | None = None
    proposal: "Card | None" = None  # the training proposal this message carries


@dataclass(frozen=True)
class Card:
    """A training proposal as its card shows it."""

    proposal: store.Proposal
    dataset_name: str | None  # None once the dataset is gone


def _tool_names() -> set[str]:
    return {tool["function"]["name"] for tool in list_tools()}


def _error_key(message: store.Message) -> str | None:
    if message.state == "cancelled":
        return "assistant.error.cancelled"
    if message.state == "failed":
        code = message.error_code if message.error_code in ERROR_CODES else "failed"
        return f"assistant.error.{code}"
    return None


def _cards(conn, conversation: Conversation) -> dict[int, Card]:
    """The conversation's proposals by message id, each with its dataset's name (only for a
    dataset of the conversation's own project)."""
    cards = {}
    for message_id, proposal in store.proposals_for(conn, conversation.id).items():
        name = None
        if proposal.dataset_id is not None:
            try:
                dataset = projects.get_dataset(conn, proposal.dataset_id)
            except DatasetNotFound:
                pass
            else:
                if dataset.project_id == conversation.project_id:
                    name = dataset.name
        cards[message_id] = Card(proposal, name)
    return cards


def _lines(messages: list[store.Message], cards: dict[int, Card]) -> list[Line]:
    """What the thread shows: the questions, Fione-kun's texts (a leading blank line of a
    reply is left out), what it looked at, the proposals it made, and why a message ended
    early."""
    tools = _tool_names()
    lines = []
    for m in messages:
        if m.role == "tool":
            name = m.tool_name if m.tool_name in tools else "refused"
            lines.append(Line("tool", f"assistant.tool.{name}", m.state))
            continue
        text = (m.content or "").lstrip("\r\n")
        error = _error_key(m)
        card = cards.get(m.id)
        if m.role == "assistant" and not text and m.state == "done" and card is None:
            continue  # a step that only called tools
        lines.append(Line(m.role, text, m.state, error, card))
    return lines


def _thread(conn, conversation: Conversation) -> dict:
    messages = store.messages(conn, conversation.id)
    return {
        "conversation": conversation,
        "lines": _lines(messages, _cards(conn, conversation)),
        "active": any(m.state in ACTIVE for m in messages),
    }


def _llm(request: Request, conn) -> dict:
    """The provider's state for the banners and the form."""
    settings = request.app.state.settings
    status = request.app.state.llm_monitor.snapshot()
    configured = settings.llm_base_url is not None
    return {
        "llm": status,
        "llm_on": configured,
        "llm_ready": configured and status.state == "ready",
        "remote_host": status.host if configured and not status.local else None,
        "samples_on": configured and store.samples_allowed(conn, settings.llm_base_url),
    }


def _prefill(request: Request, conn, ctx: Ctx) -> str:
    """The question ``?ask=model:<id>`` or ``?ask=dataset:<id>`` suggests, for an object of
    this project only; nothing is sent."""
    kind, _, oid = (request.query_params.get("ask") or "").partition(":")
    lang = language(request)
    try:
        if kind == "model":
            return i18n.t("assistant.ask_model", lang, name=model_in(conn, ctx, oid).name)
        if kind == "dataset":
            return i18n.t("assistant.ask_dataset", lang, name=dataset_in(conn, ctx, oid).name)
    except UiError:
        pass
    return ""


def _conversation(conn, ctx: Ctx, cid) -> Conversation:
    try:
        return store.get_conversation(conn, ctx.auth.user, ctx.project.id, parse_id(cid))
    except ConversationNotFound:
        raise UiError(404, "error.not_found") from None


def conversation_page(
    request: Request,
    conn,
    ctx: Ctx,
    conversation: Conversation | None,
    *,
    status: int = 200,
    notice: str | None = None,
    detail: str = "",
    text: str = "",
) -> Response:
    """The chat page showing ``conversation`` (or none), with a refusal ``notice`` (an i18n
    key, and a ``detail`` sentence after it) above the form, which holds ``text``."""
    context = {
        "conversations": store.list_conversations(conn, ctx.auth.user, ctx.project.id),
        "notice": notice,
        "detail": detail,
        "text": text,
        **_llm(request, conn),
    }
    if conversation is not None:
        context |= _thread(conn, conversation)
    return render(
        request,
        "assistant.html",
        ctx.auth,
        status=status,
        ctx=ctx,
        nav="projects",
        section="assistant",
        **context,
    )


def _page_url(pid: str, cid: int | None = None) -> str:
    return f"/projects/{pid}/assistant" + (f"?c={cid}" if cid is not None else "")


@router.get("/projects/{pid}/assistant")
def assistant(request: Request, conn: Conn, pid: str) -> Response:
    ctx = page(request, conn, pid)
    cid = request.query_params.get("c")
    if cid is not None:
        conversation = _conversation(conn, ctx, cid)
    else:
        mine = store.list_conversations(conn, ctx.auth.user, pid)
        conversation = mine[0] if mine else None
    return conversation_page(request, conn, ctx, conversation, text=_prefill(request, conn, ctx))


@router.post("/projects/{pid}/assistant/conversations")
def new_conversation(request: Request, conn: Conn, pid: str, form: SmallForm) -> Response:
    """Start a conversation, and ask its first question when the form has one."""
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    text = field(form, "text")
    try:
        conversation = store.create_conversation(conn, ctx.auth.user, pid)
    except ConversationNotFound:
        raise UiError(404, "error.not_found") from None
    except LimitReached:
        return conversation_page(
            request,
            conn,
            ctx,
            None,
            status=409,
            notice="assistant.error.conversation_limit",
            text=text,
        )
    if text.strip():
        return _ask(request, conn, ctx, conversation, text)
    return RedirectResponse(_page_url(pid, conversation.id), 303)


# A refused question: its status and text, most specific first (TurnBusy and LimitReached
# are ValueErrors, so ValueError comes last).
REFUSALS = (
    (TurnBusy, 409, "assistant.error.busy"),
    (LimitReached, 409, "assistant.error.limit"),
    (TooManyTurns, 429, "assistant.error.too_many_turns"),
    (LlmUnavailable, 503, "assistant.error.unavailable"),
    (ValueError, 422, "assistant.error.text"),
)


@router.post("/projects/{pid}/assistant/c/{cid}/messages")
def send(request: Request, conn: Conn, pid: str, cid: str, form: SmallForm) -> Response:
    """Ask Fione-kun: on to the page (HTMX: the thread, which then polls). A refusal shows
    the page with its status, a message and the question still in the form."""
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    return _ask(request, conn, ctx, _conversation(conn, ctx, cid), field(form, "text"))


def _ask(request: Request, conn, ctx: Ctx, conversation: Conversation, text: str) -> Response:
    pid = ctx.project.id
    try:
        request.app.state.turns.submit(
            conn, ctx.auth.user, pid, conversation.id, text, language=language(request)
        )
    except ConversationNotFound:
        raise UiError(404, "error.not_found") from None
    except (TurnBusy, LimitReached, TooManyTurns, LlmUnavailable, ValueError) as e:
        status, key = next((s, k) for kind, s, k in REFUSALS if isinstance(e, kind))
        return conversation_page(
            request, conn, ctx, conversation, status=status, notice=key, text=text
        )
    if request.headers.get("hx-request"):
        return _thread_fragment(request, conn, ctx, conversation)
    return RedirectResponse(_page_url(pid, conversation.id), 303)


def _thread_fragment(request: Request, conn, ctx: Ctx, conversation: Conversation) -> Response:
    context = _thread(conn, conversation)
    return render(
        request,
        "_assistant_thread.html",
        ctx.auth,
        status=200 if context["active"] else STOP_POLLING,
        ctx=ctx,
        **context,
    )


@router.get("/projects/{pid}/assistant/c/{cid}/thread")
def thread(request: Request, conn: Conn, pid: str, cid: str) -> Response:
    """The polled thread: 200 with a trigger while a message is active, then 286 with the
    stored final texts. If it can no longer be shown (the conversation deleted, access lost,
    an error), the poller gets 286 with a final message, so polling ends."""
    polling = bool(request.headers.get("hx-request"))
    try:
        ctx = page(request, conn, pid)
        return _thread_fragment(request, conn, ctx, _conversation(conn, ctx, cid))
    except UiError as e:
        if not polling or e.status == 401:  # 401: HTMX is sent to the login page
            raise
        return _thread_gone(request, e.key)
    except Exception:
        if not polling:
            raise
        log.exception("the thread of conversation %s could not be shown", cid)
        return _thread_gone(request, "error.generic")


def _thread_gone(request: Request, key: str) -> Response:
    message = i18n.t(key, language(request))
    return render(request, "_assistant_gone.html", status=STOP_POLLING, message=message)


@router.post("/projects/{pid}/assistant/c/{cid}/cancel")
def cancel(request: Request, conn: Conn, pid: str, cid: str, form: SmallForm) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    conversation = _conversation(conn, ctx, cid)  # the user's own, before the manager hears
    request.app.state.turns.cancel(conversation.id)
    return RedirectResponse(_page_url(pid, conversation.id), 303)


@router.post("/projects/{pid}/assistant/c/{cid}/delete")
def delete(request: Request, conn: Conn, pid: str, cid: str, form: SmallForm) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    conversation = _conversation(conn, ctx, cid)
    request.app.state.turns.cancel(conversation.id)
    try:
        store.delete_conversation(conn, ctx.auth.user, pid, conversation.id)
    except ConversationNotFound:
        raise UiError(404, "error.not_found") from None
    return RedirectResponse(_page_url(pid), 303)


# --- training proposals -----------------------------------------------------


def _proposal(request: Request, conn, pid: str, prid: str, token: str):
    """The signed-in user's own proposal and its conversation, for a person who can write to
    the project (404 for anyone else's, other projects' and missing ones)."""
    same_site(request)
    ctx = action(request, conn, pid, token, need="write")
    try:
        proposal = store.get_proposal(conn, ctx.auth.user, pid, parse_id(prid))
        conversation = store.get_conversation(conn, ctx.auth.user, pid, proposal.conversation_id)
    except (ProposalNotFound, ConversationNotFound):
        raise UiError(404, "error.not_found") from None
    return ctx, proposal, conversation


def _refused(request: Request, conn, ctx: Ctx, conversation, status, key, detail=""):
    return conversation_page(
        request, conn, ctx, conversation, status=status, notice=key, detail=detail
    )


@router.post("/projects/{pid}/assistant/proposals/{prid}/confirm")
def confirm(request: Request, conn: Conn, pid: str, prid: str, form: SmallForm) -> Response:
    """Start the training a proposal stores, once: the stored configuration is submitted, never
    a posted one. A decided proposal only goes back to its conversation."""
    ctx, proposal, conversation = _proposal(request, conn, pid, prid, field(form, "csrf_token"))
    back = RedirectResponse(_page_url(pid, conversation.id), 303)
    if proposal.state != "pending":
        return back

    def gone() -> Response:
        return _refused(request, conn, ctx, conversation, 409, "assistant.proposal.dataset_gone")

    if proposal.dataset_id is None:
        return gone()
    try:
        dataset = projects.get_dataset(conn, proposal.dataset_id)
    except DatasetNotFound:
        return gone()
    if dataset.project_id != pid or dataset.type != DatasetType.TRAIN:
        return gone()
    try:
        config = TrainConfig.from_dict(proposal.config)
    except ValueError as e:  # ConfigError
        return _refused(
            request, conn, ctx, conversation, 422, "assistant.proposal.failed", _reason(e)
        )
    try:
        with db.immediate(conn):
            if not store.claim_proposal(conn, proposal.id, ctx.auth.user.id):
                return back  # another confirmation came first
            job = models.submit_training(
                conn,
                request.app.state.storage,
                ctx.auth.user,
                pid,
                proposal.dataset_id,
                config,
                name=f"Fione-kun proposal {proposal.id}",
            )
            store.set_proposal_job(conn, proposal.id, job.id)
    except DatasetNotFound:
        return gone()
    except ProjectNotFound:
        raise UiError(404, "error.not_found") from None
    except PermissionError:
        raise UiError(403, "error.forbidden") from None
    except TargetError:
        return _refused(request, conn, ctx, conversation, 422, "assistant.proposal.target_data")
    except ValueError as e:  # ConfigError too; after TargetError
        return _refused(
            request, conn, ctx, conversation, 422, "assistant.proposal.failed", _reason(e)
        )
    return RedirectResponse(f"/projects/{pid}/jobs/{job.id}", 303)


def _reason(error: Exception) -> str:
    return clean_text(redact(str(error)), 300)


@router.post("/projects/{pid}/assistant/proposals/{prid}/dismiss")
def dismiss(request: Request, conn: Conn, pid: str, prid: str, form: SmallForm) -> Response:
    ctx, proposal, conversation = _proposal(request, conn, pid, prid, field(form, "csrf_token"))
    with db.immediate(conn):
        store.dismiss_proposal(conn, proposal.id, ctx.auth.user.id)
    return RedirectResponse(_page_url(pid, conversation.id), 303)

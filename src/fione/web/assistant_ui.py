"""The assistant chat page: a project's conversations of the signed-in user, the thread of one
and the question form.

Conversations are their creator's alone, so every conversation id goes through
``store.get_conversation`` (404 for anyone else's, admins included) before anything is done
with it. Messages are escaped plain text; a tool row only names what was read. While a turn
is active, HTMX polls the thread; its last answer (and any failure to show it) is 286, which
ends the polling. The page never fails because the LLM cannot be used: it says why.

The assistant's comments (notes) on a model, a failed job, a training dataset and a finished
batch prediction are fragments their pages load: any reader of the project sees the one note
of the subject in their language, which the first of them to open the page starts. Whatever
the assistant's state, the fragment is a 200 that says it; while the assistant is busy it asks
again by itself.
"""

import logging
from dataclasses import dataclass
from string import Formatter

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
from fione.assistant.turns import ERROR_CODES, LlmUnavailable, NoteView, TooManyTurns
from fione.engine.config import TargetError, TrainConfig
from fione.jobs.store import JobStatus
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
    job_in,
    model_in,
    page,
    parse_id,
    same_site,
)
from fione.web.easyml import STOP_POLLING
from fione.web.views import UiError, language, llm_status, render, to_consent

log = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)

ACTIVE = ("queued", "running")
EXAMPLES = ("1", "2", "3")  # the suggested questions of an empty conversation


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

    def warnings(self, lang: str) -> list[str]:
        """The warnings in ``lang``: a warning without a translation for its code, or without
        the figures that translation needs, is shown as its own (English) message."""
        texts = []
        for w in self.proposal.details.get("warnings") or []:
            if not isinstance(w, dict):
                texts.append(str(w))
                continue
            key, params = f"assistant.warn.{w.get('code')}", w.get("params")
            template = i18n.catalog(lang).get(key) or i18n.catalog(i18n.DEFAULT_LANGUAGE).get(key)
            needed = {name for _, name, _, _ in Formatter().parse(template or "") if name}
            if template is None or not isinstance(params, dict) or not needed <= params.keys():
                texts.append(str(w.get("message", "")))
            else:
                texts.append(i18n.t(key, lang, **params))
        return texts


def _tool_names() -> set[str]:
    return {tool["function"]["name"] for tool in list_tools()}


def _error_key(message: store.Message) -> str | None:
    if message.state == "cancelled":
        return "assistant.error.cancelled"
    if message.state == "failed":
        code = message.error_code if message.error_code in ERROR_CODES else "failed"
        return f"assistant.error.{code}"
    return None


def _cards(conn, conversation_id: int, project_id: str) -> dict[int, Card]:
    """The conversation's proposals by message id, each with its dataset's name (only for a
    dataset of the conversation's own project)."""
    cards = {}
    for message_id, proposal in store.proposals_for(conn, conversation_id).items():
        name = None
        if proposal.dataset_id is not None:
            try:
                dataset = projects.get_dataset(conn, proposal.dataset_id)
            except DatasetNotFound:
                pass
            else:
                if dataset.project_id == project_id:
                    name = dataset.name
        cards[message_id] = Card(proposal, name)
    return cards


def _lines(messages: list[store.Message], cards: dict[int, Card]) -> list[Line]:
    """What the thread shows: the questions, the assistant's texts (a leading blank line of a
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
        "lines": _lines(messages, _cards(conn, conversation.id, conversation.project_id)),
        "active": any(m.state in ACTIVE for m in messages),
    }


def _llm(request: Request) -> dict:
    """The provider's state for the explanations and the form."""
    status = llm_status(request)
    return {
        "llm": status,
        "llm_ready": status.state == "ready",
        "remote_host": None if status.local else status.host,
    }


def _prefill(request: Request, conn, ctx: Ctx) -> str:
    """The question ``?ask=model:<id>``, ``?ask=dataset:<id>`` or ``?ask=job:<id>`` (a failed
    job) suggests, for an object of this project only, or the example ``?ask=example:<n>``;
    nothing is sent."""
    kind, _, oid = (request.query_params.get("ask") or "").partition(":")
    lang = language(request)
    try:
        if kind == "model":
            return i18n.t("assistant.ask_model", lang, name=model_in(conn, ctx, oid).name)
        if kind == "dataset":
            return i18n.t("assistant.ask_dataset", lang, name=dataset_in(conn, ctx, oid).name)
        if kind == "job" and (job := job_in(conn, ctx, oid)).status == JobStatus.FAILED:
            return i18n.t("assistant.ask_job", lang, id=job.id)
        if kind == "example" and oid in EXAMPLES:
            return i18n.t(f"assistant.example_{oid}", lang)
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
        "examples": EXAMPLES,
        **_llm(request),
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
    if redirect := to_consent(request, ctx.auth):
        return redirect
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
    """Ask the assistant: on to the page (HTMX: the thread, which then polls). A refusal shows
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
    """The signed-in user's own proposal and its conversation (a chat or a note's), for a
    person who can write to the project (404 for anyone else's, other projects' and missing
    ones)."""
    same_site(request)
    ctx = action(request, conn, pid, token, need="write")
    try:
        proposal = store.get_proposal(conn, ctx.auth.user, pid, parse_id(prid))
        conversation = store.get_conversation(
            conn, ctx.auth.user, pid, proposal.conversation_id, kind=None
        )
    except (ProposalNotFound, ConversationNotFound):
        raise UiError(404, "error.not_found") from None
    return ctx, proposal, conversation


def _back(conn, pid: str, conversation: Conversation) -> RedirectResponse:
    """Back to the proposal's conversation, or for a note's, to the page of its subject."""
    if conversation.kind != "note":
        return RedirectResponse(_page_url(pid, conversation.id), 303)
    note = store.note_of(conn, conversation.id)
    if note is None:
        return RedirectResponse(_page_url(pid), 303)
    where = NOTE_SUBJECTS[note.kind]
    return RedirectResponse(f"/projects/{pid}/{where.path}/{note.subject_id}{where.back}", 303)


def _refused(request: Request, conn, ctx: Ctx, conversation, status, key, detail=""):
    """The chat page with the refusal; a note's thread is not shown there."""
    shown = None if conversation.kind == "note" else conversation
    return conversation_page(request, conn, ctx, shown, status=status, notice=key, detail=detail)


@router.post("/projects/{pid}/assistant/proposals/{prid}/confirm")
def confirm(request: Request, conn: Conn, pid: str, prid: str, form: SmallForm) -> Response:
    """Start the training a proposal stores, once: the stored configuration is submitted, never
    a posted one. A decided proposal only goes back to its conversation (or note's subject)."""
    ctx, proposal, conversation = _proposal(request, conn, pid, prid, field(form, "csrf_token"))
    back = _back(conn, pid, conversation)
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
    # The claim is short and alone in its transaction: it makes the one job of the proposal.
    # The data is read for the checks of submit_training outside any lock (it may be on S3).
    with db.immediate(conn):
        claimed = store.claim_proposal(conn, proposal.id, ctx.auth.user.id)
    if not claimed:
        return back  # another confirmation came first
    try:
        try:
            job = models.submit_training(
                conn,
                request.app.state.storage,
                ctx.auth.user,
                pid,
                proposal.dataset_id,
                config,
                name=f"Assistant proposal {proposal.id}",
            )
        except BaseException:
            with db.immediate(conn):  # no job: the proposal waits for the next try
                store.release_proposal(conn, proposal.id)
            raise
        with db.immediate(conn):
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
    return _back(conn, pid, conversation)


# --- the assistant's comments -----------------------------------------------


@dataclass(frozen=True)
class NoteSubject:
    """Where a kind of note lives: its subject's path segment, the fragment's name, the page a
    decided proposal returns to (after the subject's own path) and its ``?ask=`` prefill."""

    path: str
    fragment: str
    back: str = ""
    ask: str | None = None  # None: the plain assistant page


# A note's kind -> where it lives.
NOTE_SUBJECTS = {
    "model": NoteSubject("models", "comment", ask="model"),
    "failed_job": NoteSubject("jobs", "comment", ask="job"),
    "dataset": NoteSubject("datasets", "comment", "/analyze", ask="dataset"),
    "prediction": NoteSubject("jobs", "prediction-comment", "/result"),
}


def _note_subject(conn, ctx: Ctx, kind: str, sid) -> tuple[int, dict[str, int] | None]:
    """The id of the note's subject in the project and the integer facts its request names: a
    model, a training job that failed, a training dataset, or a finished batch prediction
    with its model and output dataset."""
    if kind == "model":
        return model_in(conn, ctx, sid).id, None
    if kind == "dataset":
        dataset = dataset_in(conn, ctx, sid)
        if dataset.type != DatasetType.TRAIN:
            raise UiError(404, "error.not_found")
        return dataset.id, None
    job = job_in(conn, ctx, sid)
    if kind == "prediction":
        model_id = job.payload.get("model_id")
        output = (job.result or {}).get("dataset_id")
        if (
            job.kind != "batch_predict"
            or job.status != JobStatus.DONE
            or type(model_id) is not int
            or type(output) is not int
        ):
            raise UiError(404, "error.not_found")
        dataset_in(conn, ctx, str(output))  # still there, in the project
        return job.id, {"model": model_id, "output": output}
    if job.kind != "automl" or job.status != JobStatus.FAILED:
        raise UiError(404, "error.not_found")
    return job.id, None


def _note_fragment(request: Request, conn, ctx: Ctx, kind: str, sid, *, retry=False) -> Response:
    subject, facts = _note_subject(conn, ctx, kind, sid)
    pid = ctx.project.id
    where = NOTE_SUBJECTS[kind]
    note = {
        "url": f"/projects/{pid}/{where.path}/{subject}/{where.fragment}",
        "ask": f"/projects/{pid}/assistant" + (f"?ask={where.ask}:{subject}" if where.ask else ""),
    }
    manager = request.app.state.turns
    write = manager.retry if retry else manager.explain
    try:
        view: NoteView = write(
            conn, ctx.auth.user, pid, kind, str(subject), language(request), facts=facts
        )
    except LlmUnavailable:
        status = llm_status(request)
        if status.error_code == "unauthorized":
            message = "assistant.error.unauthorized"
        elif status.state != "ready":
            message = f"assistant.state.{status.state}"
        else:
            message = "assistant.error.unavailable"
        note |= {"state": "unavailable", "message": message}
    except TooManyTurns:
        note |= {"state": "busy"}
    except Exception:
        log.exception("the assistant's comment on %s %s could not be shown", kind, subject)
        note |= {"state": "failed", "message": "assistant.error.failed"}
    else:
        note |= {"state": view.state, "text": view.text}
        if view.state == "failed":
            note["message"] = f"assistant.error.{view.error_code}"
        if view.state == "done":
            note["owner"] = view.owner_id == ctx.auth.user.id
            try:
                cards = _cards(conn, view.conversation_id, pid)
            except Exception:  # the comment is still worth showing without its proposal
                log.exception(
                    "the proposal of the comment on %s %s could not be shown", kind, subject
                )
            else:
                note["card"] = next(iter(cards.values()), None)
    return render(request, "_assistant_note.html", ctx.auth, ctx=ctx, note=note)


@router.get("/projects/{pid}/models/{mid}/comment")
def model_comment(request: Request, conn: Conn, pid: str, mid: str) -> Response:
    return _note_fragment(request, conn, page(request, conn, pid), "model", mid)


@router.get("/projects/{pid}/jobs/{jid}/comment")
def job_comment(request: Request, conn: Conn, pid: str, jid: str) -> Response:
    return _note_fragment(request, conn, page(request, conn, pid), "failed_job", jid)


@router.get("/projects/{pid}/datasets/{did}/comment")
def dataset_comment(request: Request, conn: Conn, pid: str, did: str) -> Response:
    return _note_fragment(request, conn, page(request, conn, pid), "dataset", did)


@router.get("/projects/{pid}/jobs/{jid}/prediction-comment")
def prediction_comment(request: Request, conn: Conn, pid: str, jid: str) -> Response:
    return _note_fragment(request, conn, page(request, conn, pid), "prediction", jid)


@router.post("/projects/{pid}/models/{mid}/comment/retry")
def retry_model_comment(
    request: Request, conn: Conn, pid: str, mid: str, form: SmallForm
) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    return _note_fragment(request, conn, ctx, "model", mid, retry=True)


@router.post("/projects/{pid}/jobs/{jid}/comment/retry")
def retry_job_comment(
    request: Request, conn: Conn, pid: str, jid: str, form: SmallForm
) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    return _note_fragment(request, conn, ctx, "failed_job", jid, retry=True)


@router.post("/projects/{pid}/datasets/{did}/comment/retry")
def retry_dataset_comment(
    request: Request, conn: Conn, pid: str, did: str, form: SmallForm
) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    return _note_fragment(request, conn, ctx, "dataset", did, retry=True)


@router.post("/projects/{pid}/jobs/{jid}/prediction-comment/retry")
def retry_prediction_comment(
    request: Request, conn: Conn, pid: str, jid: str, form: SmallForm
) -> Response:
    same_site(request)
    ctx = action(request, conn, pid, field(form, "csrf_token"), need="read")
    return _note_fragment(request, conn, ctx, "prediction", jid, retry=True)

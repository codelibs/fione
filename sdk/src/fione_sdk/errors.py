from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fione_sdk.jobs import Job


class FioneError(Exception):
    """An error from the Fione API (``status`` is the HTTP status, 0 when no HTTP
    response is involved: a configuration error or a failed job) with the API's error ``code``
    slug and ``message``."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{message} ({code}, HTTP {status})" if status else message)
        self.status = status
        self.code = code
        self.message = message

    def __reduce__(self):
        return (type(self), (self.status, self.code, self.message))


class JobFailed(FioneError):
    """A job that ended as ``failed`` or ``cancelled`` (the error's ``code``); ``message`` is
    the job's own message and ``job`` the job as it ended."""

    def __init__(self, job: "Job"):
        status = job.status
        super().__init__(0, status, job.data.get("message") or f"job {job.id} {status}")
        self.job = job

    def __reduce__(self):
        return (type(self), (self.job,))

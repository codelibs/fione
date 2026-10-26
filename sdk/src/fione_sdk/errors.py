class FioneError(Exception):
    """An error from the Fione API (``status`` is the HTTP status, 0 for a client-side
    configuration error) with the API's error ``code`` slug and ``message``."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{message} ({code}, HTTP {status})" if status else message)
        self.status = status
        self.code = code
        self.message = message

    def __reduce__(self):
        return (type(self), (self.status, self.code, self.message))

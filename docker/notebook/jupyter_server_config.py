"""Jupyter Server settings of the notebook image (docker/Dockerfile.notebook): the
fione_notebook extension, set from the FIONE_NB_* values the launcher passes to the container.
The server exits when one is missing or the image's Jupyter dirs are writable."""

import os

try:
    from fione_notebook.config import configure

    configure(get_config(), os.environ)  # noqa: F821
except Exception as error:
    # traitlets logs any other error in a config file and starts a stock server, so any error
    # must exit too. Only the class name: the message may hold a FIONE_NB_* value.
    raise SystemExit(f"fione_notebook: configuration failed ({type(error).__name__})") from None

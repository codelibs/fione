"""Jupyter Server settings of the notebook image (docker/Dockerfile.notebook): the
fione_notebook extension, set from the FIONE_NB_* values the launcher passes to the container.
The server exits when one is missing or the image's Jupyter dirs are writable."""

import os

from fione_notebook.config import configure

configure(get_config(), os.environ)  # noqa: F821

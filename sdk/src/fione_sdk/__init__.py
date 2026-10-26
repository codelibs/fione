"""Python client for Fione: use it from a notebook or a script."""

from fione_sdk.client import Client
from fione_sdk.errors import FioneError

__version__ = "20.0.0"

__all__ = ["Client", "FioneError", "__version__"]

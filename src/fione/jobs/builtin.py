"""Imports the built-in handler modules so that they register; every worker loads this."""

from fione.jobs import (  # noqa: F401
    automl_handler,
    batch_predict_handler,
    export_handler,
    module_handler,
)

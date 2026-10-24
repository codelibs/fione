"""Imports the built-in handler modules so that they register; every worker loads this."""

from fione.jobs import automl_handler, batch_predict_handler, export_handler  # noqa: F401

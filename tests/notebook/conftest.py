import importlib.util

# These tests need the notebook dependency group (`uv sync --group notebook`). Marker
# deselection happens after collection, and collecting them imports Jupyter, so without the
# group they are not collected at all.
if importlib.util.find_spec("jupyter_server") is None:
    collect_ignore_glob = ["test_*.py"]

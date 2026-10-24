"""``python -m fione_serving``: serve the model in ``$FIONE_MODEL_DIR`` on ``0.0.0.0:$PORT``."""

import logging
import os
import sys

import uvicorn

from fione_serving.app import create_app
from fione_serving.loader import ModelLoadError

log = logging.getLogger("fione_serving")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        app = create_app()
    except ModelLoadError as e:
        log.error("%s", e)
        return 1
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_config=None)  # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())

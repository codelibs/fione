"""``python -m fione_launcher``: serve the launcher API on port 8000."""

import sys

from fione_launcher.server import main

if __name__ == "__main__":
    sys.exit(main())

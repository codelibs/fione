#!/bin/sh
# Start Fione: make the temp dir on the data volume, create the S3 bucket on first start
# (when the storage is S3), then serve with uvicorn.
set -eu

mkdir -p "${TMPDIR:-/data/tmp}"

python - <<'EOF'
from fione.config import get_settings
from fione.storage import S3Storage, open_storage

storage = open_storage(get_settings())
if isinstance(storage, S3Storage):
    storage.ensure_bucket()  # a no-op once it exists
EOF

# Exactly one worker process, on purpose: the login throttle, the upload and password-hash
# limits, the one-time handoff of new API tokens and the job runner all live in the
# process's memory; several workers would each keep their own (and run the queue twice).
# Proxy headers are left to Fione's own FIONE_TRUST_PROXY setting.
exec uvicorn fione.api.app:create_app --factory \
    --host 0.0.0.0 --port 8080 --workers 1 --no-proxy-headers "$@"

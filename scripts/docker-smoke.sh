#!/usr/bin/env bash
# Build the images, start the end-to-end stack (docker/compose.e2e.yaml), wait for it to be
# healthy, check the status endpoints and the vendored front-end, then remove the stack with
# its volumes, whatever happened (trap).
#
#   scripts/docker-smoke.sh
#   FIONE_SMOKE_PROJECT=fione-smoke FIONE_PORT=18090 scripts/docker-smoke.sh   # elsewhere
#
# The project defaults to fione-e2e on port 18080. The script refuses to run when that
# project already has containers or volumes (a stack it did not start), so it only ever
# removes what it created itself. Exits non-zero on any failure.
set -euo pipefail

cd "$(dirname "$0")/.."
project="${FIONE_SMOKE_PROJECT:-fione-e2e}"
compose=(docker compose -p "$project" --env-file docker/e2e.env
    -f docker/compose.yaml -f docker/compose.e2e.yaml)
base="http://127.0.0.1:${FIONE_PORT:-18080}"

existing=$("${compose[@]}" ps -a -q)
existing+=$(docker volume ls -q --filter "label=com.docker.compose.project=$project")
if [ -n "$existing" ]; then
    echo "project $project already has containers or volumes: not touching it" >&2
    exit 1
fi

cookies=$(mktemp)
cleanup() {
    status=$?
    rm -f "$cookies"
    if [ "$status" -ne 0 ]; then
        "${compose[@]}" logs --tail 50 || true
    fi
    "${compose[@]}" down -v --remove-orphans || true
    exit "$status"
}
trap cleanup EXIT

check() {  # check NAME COMMAND...: run it, say which check failed
    if ! "${@:2}"; then
        echo "FAILED: $1" >&2
        return 1
    fi
    echo "ok: $1"
}

"${compose[@]}" --profile serving build
"${compose[@]}" up -d --wait --wait-timeout 180

check "health" curl -fsS "$base/api/v1/health" -o /dev/null
status=$(curl -fsS "$base/api/v1/auth/status")
check "first admin needed" grep -q '"needs_first_admin":true' <<<"$status"
check "login page" curl -fsS "$base/login" -o /dev/null
check "vendored htmx" curl -fsS "$base/static/vendor/htmx/htmx.min.js" -o /dev/null
check "vendored echarts" curl -fsS "$base/static/vendor/echarts/echarts.min.js" -o /dev/null
token=$(sed -n 's/^FIONE_SETUP_TOKEN=//p' docker/e2e.env)
check "first admin" curl -fsS -c "$cookies" -o /dev/null -H "Content-Type: application/json" \
    -d "{\"username\":\"smoke-admin\",\"password\":\"smoke-password-1\",\"setup_token\":\"$token\"}" \
    "$base/api/v1/auth/first-admin"
status=$(curl -fsS -b "$cookies" "$base/api/v1/system/status")
check "system status: S3 storage" grep -q '"storage":"s3"' <<<"$status"
check "system status: runner" grep -q '"runner":"running"' <<<"$status"
check "system status: no credentials" bash -c '! grep -qiE "NotForRealUse|seaweedfs:8333|secret" <<<"$1"' _ "$status"
uid=$("${compose[@]}" exec -T fione id -u)  # a failing exec ends the script here
check "runs as non-root" test -n "$uid" -a "$uid" != 0
check "one uvicorn worker" test "$("${compose[@]}" exec -T fione ps -eo args | grep -c '[u]vicorn fione.api.app')" = 1
echo "docker smoke test passed"

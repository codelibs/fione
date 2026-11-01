#!/usr/bin/env bash
# Build the images, start the end-to-end stack (docker/compose.e2e.yaml), wait for it to be
# healthy, check the status endpoints, the vendored front-end and the MCP endpoint, then
# remove the stack with its volumes, whatever happened (trap).
#
#   scripts/docker-smoke.sh
#   FIONE_SMOKE_PROJECT=fione-smoke FIONE_PORT=18090 \
#       scripts/docker-smoke.sh   # elsewhere
#
# The project defaults to fione-e2e on port 18080. The script refuses to run when
# that project already has containers or volumes (a stack it did not start), so it only ever
# removes what it created itself. Exits non-zero on any failure.
set -euo pipefail

cd "$(dirname "$0")/.."
project="${FIONE_SMOKE_PROJECT:-fione-e2e}"
# The shell's own FIONE_* settings (a real deployment's keys, say) must not reach this
# throwaway stack: compose prefers them over docker/e2e.env. Only the tag and port pass.
for name in $(compgen -e); do
    case "$name" in
        FIONE_IMAGE_TAG | FIONE_PORT) ;;
        FIONE_*) unset "$name" ;;
    esac
done
# An exported COMPOSE_PROFILES=ollama would start a real Ollama and download 8 GB.
unset COMPOSE_PROFILES
compose=(docker compose -p "$project" --env-file docker/e2e.env
    -f docker/compose.yaml -f docker/compose.e2e.yaml)
base="http://127.0.0.1:${FIONE_PORT:-18080}"

existing=$("${compose[@]}" --profile serving ps -a -q)
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
    "${compose[@]}" --profile serving down -v --remove-orphans || true
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
admin=$(curl -fsS -c "$cookies" -H "Content-Type: application/json" \
    -d "{\"username\":\"smoke-admin\",\"password\":\"smoke-password-1\",\"setup_token\":\"$token\"}" \
    "$base/api/v1/auth/first-admin") || { echo "FAILED: first admin" >&2; exit 1; }
echo "ok: first admin"
status=$(curl -fsS -b "$cookies" "$base/api/v1/system/status")
check "system status: S3 storage" grep -q '"storage":"s3"' <<<"$status"
check "system status: runner" grep -q '"runner":"running"' <<<"$status"
check "system status: no credentials" bash -c '! grep -qiE "NotForRealUse|seaweedfs:8333|secret" <<<"$1"' _ "$status"
# Fione-kun: the fake LLM downloads its model at the first probe; the state turns ready.
llm_ready() { curl -fsS -b "$cookies" "$base/api/v1/system/status" | grep -q '"llm":{[^}]*"state":"ready"'; }
for _ in $(seq 60); do llm_ready && break; sleep 1; done
check "system status: Fione-kun ready" llm_ready
# MCP (on in this stack): initialize answers with an API token, and without one 401.
csrf=$(sed -n 's/.*"csrf_token":"\([^"]*\)".*/\1/p' <<<"$admin")
api_token=$(curl -fsS -b "$cookies" -H "X-CSRF-Token: $csrf" -H "Content-Type: application/json" \
    -d '{"name":"smoke"}' "$base/api/v1/tokens" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
check "api token created" test -n "$api_token"
initialize='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}}'
mcp_status() {  # mcp_status [CURL ARGS...]: the HTTP status of initialize
    curl -sS -o /dev/null -w '%{http_code}' -H "Content-Type: application/json" "$@" \
        -d "$initialize" "$base/mcp"
}
check "mcp: initialize with a token" test "$(mcp_status -H "Authorization: Bearer $api_token")" = 200
check "mcp: refused without a token" test "$(mcp_status)" = 401
uid=$("${compose[@]}" exec -T fione id -u)  # a failing exec ends the script here
check "runs as non-root" test -n "$uid" -a "$uid" != 0
check "one uvicorn worker" test "$("${compose[@]}" exec -T fione ps -eo args | grep -c '[u]vicorn fione.api.app')" = 1
echo "docker smoke test passed"

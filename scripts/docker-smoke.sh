#!/usr/bin/env bash
# Build the images, start the end-to-end stack (docker/compose.e2e.yaml) with the notebook
# profile, wait for it to be healthy, check the status endpoints, the vendored front-end and
# the notebook topology, then remove the stack with its volumes and any notebook containers
# and volumes, whatever happened (trap).
#
#   scripts/docker-smoke.sh
#   FIONE_SMOKE_PROJECT=fione-smoke FIONE_PORT=18090 FIONE_NOTEBOOK_PORT=18898 \
#       scripts/docker-smoke.sh   # elsewhere
#
# The project defaults to fione-e2e on ports 18080 and 18888. The script refuses to run when
# that project already has containers or volumes (a stack it did not start), so it only ever
# removes what it created itself. Exits non-zero on any failure.
set -euo pipefail

cd "$(dirname "$0")/.."
project="${FIONE_SMOKE_PROJECT:-fione-e2e}"
# The shell's own FIONE_* settings (a real deployment's keys, say) must not reach this
# throwaway stack: compose prefers them over docker/e2e.env. Only the tag and port pass.
for name in $(compgen -e); do
    case "$name" in
        FIONE_IMAGE_TAG | FIONE_PORT | FIONE_NOTEBOOK_PORT) ;;
        FIONE_*) unset "$name" ;;
    esac
done
compose=(docker compose -p "$project" --env-file docker/e2e.env
    -f docker/compose.yaml -f docker/compose.e2e.yaml --profile notebook)
base="http://127.0.0.1:${FIONE_PORT:-18080}"
notebook_base="http://127.0.0.1:${FIONE_NOTEBOOK_PORT:-18888}"

# The notebook containers and volumes the launcher creates carry fione.project=<project>.
labelled() {  # labelled KIND: the ids of this project's notebook containers or volumes
    if [ "$1" = container ]; then
        docker ps -a -q --filter "label=fione.project=$project"
    else
        docker volume ls -q --filter "label=fione.project=$project"
    fi
}

existing=$("${compose[@]}" --profile serving ps -a -q)
existing+=$(docker volume ls -q --filter "label=com.docker.compose.project=$project")
existing+=$(labelled container)
existing+=$(labelled volume)
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
    labelled container | xargs -r docker rm -f >/dev/null || true
    "${compose[@]}" --profile serving down -v --remove-orphans || true
    labelled volume | xargs -r docker volume rm >/dev/null || true
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

check "notebook gateway: nothing at /" test "$(curl -sS -o /dev/null -w '%{http_code}' "$notebook_base/")" = 404
launcher=$("${compose[@]}" ps -q notebook-launcher)
check "launcher healthy" test "$(docker inspect -f '{{.State.Health.Status}}' "$launcher")" = healthy
check "launcher publishes nothing" test -z "$(docker port "$launcher")"
fione_id=$(docker inspect -f '{{.Id}}' "$("${compose[@]}" ps -q fione)")
members=$(docker network inspect -f '{{range $id, $c := .Containers}}{{$id}} {{end}}' "${project}_notebooks")
check "fione not on notebooks" bash -c '! grep -qw "$1" <<<"$2"' _ "$fione_id" "$members"
check "notebook-image not started" test -z "$("${compose[@]}" ps -a -q notebook-image)"
tag=${FIONE_IMAGE_TAG:-$(sed -n 's/^FIONE_IMAGE_TAG=//p' docker/e2e.env)}
check "notebook image built" test -n "$(docker image inspect -f '{{.Id}}' "ghcr.io/codelibs/fione-notebook:$tag")"
echo "docker smoke test passed"

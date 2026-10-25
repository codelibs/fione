# Fione: the web UI, the REST API and the job runner in one container (data under /data).
#
#   docker build -f docker/Dockerfile --build-arg FIONE_IMAGE_TAG=<version> \
#       -t ghcr.io/codelibs/fione:<version> .
#
# Usually built and started by docker/compose.yaml, with SeaweedFS as the object storage.
# FIONE_IMAGE_TAG is recorded in every trained model; the serving image
# (docker/Dockerfile.serving) must be built with the same value to load those models.

FROM python:3.12.15-slim-trixie AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_NO_CACHE=1

# The locked runtime dependencies first (no dev group: no pytest, no Playwright), so that a
# source change does not reinstall them. The project itself runs from src/ (PYTHONPATH).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN python -m compileall -q src


FROM python:3.12.15-slim-trixie

ARG FIONE_IMAGE_TAG=dev

# procps: `ps`, which the job runner uses to tell its own orphaned workers from other
# processes. libgomp1: the OpenMP runtime LightGBM and XGBoost need.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Not root. /data is the volume: the database, the secret key, local objects and the temp
# files of uploads and imports (TMPDIR), which can need about twice the upload size.
RUN useradd --uid 10001 --home-dir /data --no-create-home --shell /usr/sbin/nologin fione \
    && install -d -o fione -g fione /data /data/tmp

COPY --from=build /app /app
COPY --chmod=0755 docker/fione-entrypoint.sh /usr/local/bin/fione-entrypoint

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    HOME=/data \
    FIONE_DATA_DIR=/data \
    TMPDIR=/data/tmp \
    FIONE_IMAGE_TAG=${FIONE_IMAGE_TAG}

USER 10001
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=3)"]

ENTRYPOINT ["fione-entrypoint"]

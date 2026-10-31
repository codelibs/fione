# Configuration

Fione is configured with environment variables. In the Docker Compose setup
(`docker/compose.yaml`) most of them are already set; you only fill in `docker/.env`
(see [Quick start](quickstart.md)).

## Fione settings

Read by the `fione` container at start. Booleans accept `true` / `false`.

| Variable | Default | What it does | When to change it |
|---|---|---|---|
| `FIONE_DATA_DIR` | `/data` | The data directory: the SQLite database, the secret key, job logs, temp files, and the objects when the storage is local. | Only outside the container image. |
| `FIONE_STORAGE_URL` | `file://<data dir>/objects` | Where datasets and models are stored: `file:///absolute/path` or `s3://bucket[/prefix]`. Compose sets `s3://fione` (SeaweedFS). | To use another S3-compatible storage. The bucket must exist, or be creatable by the S3 identity (the container creates it at start). |
| `FIONE_SECRET_KEY_PATH` | `<data dir>/secret.key` | The install's secret key (32 random bytes, created on first start, mode 0600). It signs sessions and model files. | Rarely. See [The secret key](#the-secret-key). |
| `FIONE_S3_ENDPOINT` | unset | The S3 endpoint URL (path-style addressing). Compose: `http://seaweedfs:8333`. | With another S3 server. |
| `FIONE_S3_ACCESS_KEY` | unset | The S3 access key. Compose takes it from `docker/.env`. | Always set your own. |
| `FIONE_S3_SECRET_KEY` | unset | The S3 secret key. Compose takes it from `docker/.env`. | Always set your own. |
| `FIONE_S3_REGION` | `us-east-1` | The S3 region name. | For AWS S3 outside `us-east-1`. |
| `FIONE_MAX_CONCURRENT_TRAIN_JOBS` | `1` | How many training jobs run at once; others wait in the queue. Each training uses all CPU cores. | Only on large machines. |
| `FIONE_MAX_CONCURRENT_SHORT_JOBS` | `4` | How many other jobs (predictions, explanations, exports, Python modules) run at once. | Rarely. |
| `FIONE_IMAGE_TAG` | `dev` (baked into the image) | The image's version tag. Every trained model records it, and Fione Serving only loads models of its own tag. | Set at build time (`--build-arg FIONE_IMAGE_TAG=…`), not at run time. |
| `FIONE_SERVING_IMAGE` | `ghcr.io/codelibs/fione-serving` | The serving image named in the `docker run` command the UI shows. | If you publish the serving image elsewhere. |
| `FIONE_EXPLAIN_AFTER_TRAINING` | `true` | Queues a short explain job after each training: the inputs' importance and the partial dependence curves of the 10 most important, computed on a sample of the training data. | Set `false` to explain models only when someone asks (saves CPU on busy installs). |
| `FIONE_RUNNER_ENABLED` | `true` | Runs the job queue in the app. With `false`, jobs are queued but never run. | Not in normal use (tests). |
| `FIONE_COOKIE_SECURE` | `false` | Marks the session and preference cookies `Secure` (HTTPS only). | Set `true` when users reach Fione over HTTPS. |
| `FIONE_SESSION_MAX_AGE_SECS` | `604800` (7 days) | How long a sign-in lasts. | To sign users out sooner. |
| `FIONE_LOGIN_MAX_FAILURES` | `5` | Failed password checks per (client address, username) in the window before sign-in is refused for a while. | Rarely. |
| `FIONE_LOGIN_WINDOW_SECS` | `900` (15 min) | The window of the two limits above and below. | Rarely. |
| `FIONE_LOGIN_MAX_FAILURES_PER_IP` | `50` | Failed password checks per client address in the window, whatever the usernames. | See [Behind a reverse proxy](#behind-a-reverse-proxy). |
| `FIONE_TRUST_PROXY` | `false` | Takes the client address and host from `X-Forwarded-For` / `X-Forwarded-Host` (the last value, the one your proxy added). | Set `true` only behind a reverse proxy that sets these headers. |
| `FIONE_MAX_UPLOAD_BYTES` | `1073741824` (1 GiB) | The largest CSV upload. | To allow bigger or smaller uploads (mind the temp space). |
| `FIONE_SETUP_TOKEN` | unset | The token that creates the first administrator, at least 16 characters. When unset, Fione generates one and writes it to the log at every start until an administrator exists. | To choose it yourself (`docker/.env`). |
| `FIONE_NOTEBOOK_URL` | unset | The notebook gateway's origin as browsers reach it (`scheme://host[:port]`, no path), for example `http://localhost:8888`. Setting it turns on the notebook page; `FIONE_PUBLIC_URL`, `FIONE_NOTEBOOK_LAUNCHER_URL` and `FIONE_NOTEBOOK_LAUNCHER_SECRET` are then required. It must differ from Fione's origin (a default port such as `:443` counts as the same origin) but be on the same site (the same host name with another port, or a sibling subdomain). | To use notebooks. |
| `FIONE_PUBLIC_URL` | unset | Fione's own origin as browsers reach it (`scheme://host[:port]`, no path), for example `https://fione.example.com`. Notebooks accept only this origin. | With notebooks. Behind a TLS proxy, give the `https` origin: Fione cannot tell it. |
| `FIONE_NOTEBOOK_LAUNCHER_URL` | unset | The notebook launcher's URL. Compose: `http://notebook-launcher:8000`. | With notebooks, outside Compose. |
| `FIONE_NOTEBOOK_LAUNCHER_SECRET` | unset | The secret shared with the notebook launcher, at least 32 visible ASCII characters. | With notebooks: generate it, for example `openssl rand -hex 32`. |
| `FIONE_NOTEBOOK_MAX_LIFETIME_SECS` | `43200` (12 h) | How long a notebook runs at most: its container, its sign-in and its API token. From 600 to 604800 (7 days). | To end notebooks sooner or let them run longer. |

Fixed limits that are not settings: a model import file can be up to 512 MiB, an uploaded
Python module up to 256 KiB.

## Compose variables (`docker/.env`)

Used by `docker/compose.yaml` (see `docker/.env.example`).

| Variable | Required | What it does |
|---|---|---|
| `FIONE_S3_ACCESS_KEY` | yes | The S3 identity shared by Fione and SeaweedFS. Generate it, for example `openssl rand -hex 16`. |
| `FIONE_S3_SECRET_KEY` | yes | Its secret, for example `openssl rand -hex 32`. |
| `FIONE_SETUP_TOKEN` | no | A fixed first-administrator token (see above). |
| `FIONE_IMAGE_TAG` | no | The tag every image is built with (default `dev`). |
| `FIONE_PORT` | no | The host port of the web UI (default `8080`, on 127.0.0.1). |
| `FIONE_SERVING_PORT` | no | The host port of the optional `fione-serving` service (default `8081`). |
| `FIONE_MODEL_DIR` | no | The model directory the `fione-serving` service mounts (default `./model`). |
| `FIONE_PUBLIC_URL` | with notebooks | Fione's origin as browsers reach it, passed to Fione (see above). |
| `FIONE_NOTEBOOK_URL` | with notebooks | The notebook gateway's origin as browsers reach it, passed to Fione (see above). Empty: notebooks are off. |
| `FIONE_NOTEBOOK_LAUNCHER_SECRET` | with notebooks | The secret Fione and the `notebook-launcher` service share. Generate it, for example `openssl rand -hex 32`. |
| `FIONE_NOTEBOOK_PORT` | no | The host port of the `notebook-gateway` service (default `8888`, on 127.0.0.1). |
| `FIONE_NOTEBOOK_MAX_LIFETIME_SECS` | no | Passed to Fione (default `43200`, see above). |
| `FIONE_NOTEBOOK_MAX_RUNNING` | no | Passed to the `notebook-launcher` service (default `4`, see below). |

Compose refuses to start while `FIONE_S3_ACCESS_KEY` or `FIONE_S3_SECRET_KEY` is empty. The
two S3 values may only use `A-Z a-z 0-9 / + = . _ -`; SeaweedFS refuses to start otherwise.

The notebook services are in the Compose profile `notebook`: build and start them with
`--profile notebook`. Compose sets `FIONE_NOTEBOOK_LAUNCHER_URL` itself. `FIONE_PUBLIC_URL`
and `FIONE_NOTEBOOK_URL` must use the same host name (`localhost` and `127.0.0.1` are
different sites, and the notebook frame then cannot sign in). The gateway
(`docker/notebook-gateway.conf`) publishes JupyterLab on port 8888 and relays the notebooks'
API calls to Fione on port 8081, inside Compose only; the relay refuses `/api/v1/auth`,
`/api/v1/tokens`, `/api/v1/users` and raw paths with a `.` or `..` segment (see
[Known limitations](known-limitations.md#notebooks)). Behind HTTPS, JupyterLab's `_xsrf` cookie is not marked
`Secure`; it guards form posts and is not a credential.

## Fione Serving

The serving image reads these (see [Fione Serving](serving.md)):

| Variable | Default | What it does |
|---|---|---|
| `FIONE_MODEL_DIR` | `/model` | The model directory (`manifest.json` and `model.joblib`). |
| `FIONE_IMAGE_TAG` | the image's tag | Must equal the tag recorded in the model. |
| `FIONE_SERVING_MAX_BODY` | `10485760` (10 MiB) | The largest `/invocations` request body. |
| `FIONE_SERVING_MAX_INSTANCES` | `10000` | The most instances in one request. |
| `FIONE_SERVING_MAX_CONTRIBUTION_INSTANCES` | `100` | The most instances in one request that asks for contributions (`"contributions": true`). Plain predictions wait while such a request computes; a lower value shortens the wait. |
| `FIONE_SERVING_MAX_CONTRIBUTION_REQUESTS` | `2` | How many requests for contributions run at once; another one gets 503 at once. Plain predictions wait while one runs, as they share the model. |
| `PORT` | `8080` | The port inside the container. |

## fione-sdk

The Python client `fione-sdk` (in `sdk/`, install it with `pip install ./sdk`) reads these
when you create a `Client` without arguments:

| Variable | What it does |
|---|---|
| `FIONE_URL` | The address of the Fione server, for example `http://localhost:8080`. |
| `FIONE_TOKEN` | An API token (see the Account page). Sent as `Authorization: Bearer`. |

## Notebook launcher

The `notebook-launcher` service of the Compose profile `notebook` starts one JupyterLab
container per user for Fione (see [Notebooks](notebook.md)). It is the only service with the Docker socket. It reads these at
start and exits when one is missing or malformed:

| Variable | Default | What it does |
|---|---|---|
| `FIONE_LAUNCHER_SECRET` | none (required) | The secret Fione sends in `X-Fione-Launcher-Secret`. At least 32 characters. |
| `FIONE_NOTEBOOK_IMAGE` | none (required) | The image of the notebook containers. It must be on the host already: the launcher never pulls. |
| `FIONE_NOTEBOOK_API_URL` | `http://notebook-gateway:8081` | The address a notebook's fione-sdk uses (its `FIONE_URL`): the gateway's relay to Fione, as `scheme://host[:port]`. |
| `FIONE_NOTEBOOK_MAX_RUNNING` | `4` | The most notebook containers at once. Each one may use 2 CPUs and 4 GiB of memory. |

Each container gets a named volume `<project>-nb-home-<user id>` for its notebooks, labelled
`fione.project=<project>` and `fione.uid=<user id>`; stopping a notebook keeps it. The launcher
removes its project's notebook containers when it starts and stops, and removes a container
once its lifetime ends.

When an administrator deletes a user, Fione asks the launcher to remove that user's container
and volume. Fione reuses user ids: a user created later may get the deleted user's id, and with
it the same volume name. If that removal fails (the launcher is down, say), Fione deletes the
user anyway and retries the removal every minute and before every notebook start, stop and status check; no
notebook starts for that user id until it succeeds. To check, list the volumes by label as
[Notebooks](notebook.md#files-and-persistence) shows.

## Internal variables

`FIONE_JOB_DB` and `FIONE_JOB_HANDLER_MODULES` are set by Fione for its own job worker
processes. Do not set them.

## Deployment notes

### One worker process

Fione must run as **one** process with **one** uvicorn worker (the image does this). The
sign-in throttle, the upload and password-hashing limits, the one-time display of new API
tokens, the lock that keeps one user's notebook starts and stops in turn, and the job runner
all live in that process's memory. Several workers would each keep
their own limits and would run the job queue twice. Do not scale the `fione` service.

### Behind a reverse proxy

The ports are published on `127.0.0.1` only. To serve other machines, put a reverse proxy
with HTTPS in front of `127.0.0.1:8080`, and set in the `fione` service's `environment`:

```yaml
FIONE_TRUST_PROXY: "true"     # the client address from X-Forwarded-For
FIONE_COOKIE_SECURE: "true"   # cookies over HTTPS only
```

Without `FIONE_TRUST_PROXY`, every client seems to come from the proxy's address, so all
users share one budget of 50 failed sign-ins per 15 minutes (`FIONE_LOGIN_MAX_FAILURES_PER_IP`):
one person's mistakes can block sign-in for everyone. With it, Fione takes the **last**
`X-Forwarded-For` value: the address your proxy saw. Behind a chain of proxies that is the
address the nearest one saw. Never set it when clients can reach Fione directly, or they could
choose their own address.

An nginx example:

```nginx
server {
    listen 443 ssl;
    server_name fione.example.com;
    # ssl_certificate ...; ssl_certificate_key ...;

    client_max_body_size 1100m;          # the 1 GiB upload limit plus form overhead

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $http_host;  # required: forms check that Origin matches Host
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;       # stream large uploads
        proxy_read_timeout 300s;
    }
}
```

Keep the `Host` line: sign-in and every form post compare the browser's `Origin` with the
`Host` Fione sees, and without it they are refused (403).

### The setup token

While no administrator exists, the first-administrator page asks for a setup token. Unless
`FIONE_SETUP_TOKEN` is set, Fione generates one, stores it in `<data dir>/setup-token` and
writes it to the log at every start until an administrator exists:

```sh
docker compose -f docker/compose.yaml --env-file docker/.env logs fione | grep "Setup token"
```

Anyone who can read the log can create the administrator until you do, so create it soon
after the first start (or set `FIONE_SETUP_TOKEN`). The token stops working once an
administrator exists.

### The secret key

`/data/secret.key` (on the `fione-data` volume) signs sessions and the manifests of trained
models. Back it up with the volume. If it is lost or replaced, everyone has to sign in again
and the models already trained can no longer be loaded by Fione (their signature no longer
verifies); serving bundles you already downloaded keep working, because Fione Serving checks
file hashes, not the signature.

### Temporary space

Uploads and imports are spooled to `TMPDIR`, which the image sets to `/data/tmp` on the data
volume. An upload needs about twice its size while it is converted (the CSV and its Parquet
copy), so keep at least 2 GiB free for the default 1 GiB limit.

### Storage

SeaweedFS stores the datasets and models (volume `seaweed-data`; Docker names the volumes
`fione_seaweed-data` and `fione_fione-data` after the Compose project `fione`). Its S3 port is not published
on the host; only `fione` reaches it, on the Compose network `backend`. Its other ports (master,
filer, volume) need no credentials on that network, which only `fione` and SeaweedFS join. The
optional `fione-serving` service runs on a network of its own (`serving`) and cannot reach
them.

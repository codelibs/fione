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
| `FIONE_PUBLIC_URL` | unset | Fione's own origin as browsers reach it (`scheme://host[:port]`, no path), for example `https://fione.example.com`. The MCP endpoint accepts browser requests (`Origin`) only from this origin and from `localhost`. | When a browser-based MCP client reaches Fione at another address. Behind a TLS proxy, give the `https` origin: Fione cannot tell it. |
| `FIONE_LLM_BASE_URL` | unset | The LLM server for the assistant: `http(s)://host[:port][/path]`, with no credentials, query or fragment, for example `https://api.openai.com/v1` or `http://localhost:11434/v1`. Fione calls `<base URL>/chat/completions`. Unset: the assistant is off and nothing else changes. Fione's own `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and `NO_PROXY` environment variables apply to these calls. The system page marks a server as local when its host is `localhost`, a loopback address, `host.docker.internal` or a single-label name such as a Compose service; it trusts single-label names, but a resolver search domain can make one reach a remote host. | To turn the assistant on. |
| `FIONE_LLM_PROVIDER` | `openai` | `openai` for any OpenAI-compatible server (OpenAI, vLLM, llama.cpp), or `ollama`. With `ollama` the base URL must end in `/v1`, and thinking output is turned off unless `FIONE_LLM_EXTRA_BODY` says otherwise. | With Ollama. |
| `FIONE_LLM_API_KEY` | unset | The key sent as `Authorization: Bearer <key>`, visible ASCII characters. It is never logged or shown. | With a server that needs one. |
| `FIONE_LLM_MODEL` | `gemma4:12b-mlx` | The model name sent with each request, 1 to 200 visible ASCII characters. MLX models run only on an Ollama installed on the host of an Apple Silicon Mac, which Fione reaches over its API. Elsewhere (Linux, or Ollama in a container), use a non-MLX tag such as `gemma4:12b`. | To use another model, or on a machine that cannot run MLX. |
| `FIONE_LLM_EXTRA_BODY` | unset | A JSON object merged into every request, for example `{"reasoning_effort": "none"}`. The keys `model`, `messages`, `tools`, `stream`, `stream_options` and `max_tokens` are refused. Unset: `{"reasoning_effort": "none"}` for `ollama`, `{}` for `openai`. | To turn thinking off or set sampling options on a server that supports them. |
| `FIONE_LLM_AUTO_PULL` | `false` | With `ollama`: pulls the model when the server does not have it, and shows the progress on the system page. With `false`, the server's models are left to you: when the model is missing, the system page offers a button that pulls it. Ignored for `openai`. | Set `true` to pull the model without asking, for example on an Ollama server that only Fione uses. |
| `FIONE_LLM_MAX_TOKENS` | `1024` | The most tokens one completion may have. From 64 to 8192, and at least 3008 less than `FIONE_LLM_CONTEXT_TOKENS`. | For longer answers, or to cap slow models. |
| `FIONE_LLM_CONTEXT_TOKENS` | `16384` | The token budget of one request: the longest prompt Fione sends, the reply included. Up to 262144. `FIONE_LLM_CONTEXT_TOKENS` less `FIONE_LLM_MAX_TOKENS` must be at least 3008: the assistant's tools and instructions take about 2,940 tokens, so less leaves no room for a question. Set it no higher than the model's context window. With Ollama, Fione also keeps to the context the server loaded the model with, and loads the model first when it does not know that context yet. Even 4096, Ollama's default, is too small for the tools: most tool results, such as a dataset's description, are left out, so the assistant cannot read your data. Set `OLLAMA_CONTEXT_LENGTH=16384` on the Ollama server (Compose's `ollama` profile does; set it yourself for an Ollama on the host). A question that does not fit ends with an error, never cut short. | To match the model's context window. |
| `FIONE_LLM_MAX_TOOL_ROUNDS` | `6` | How many times one answer may call tools before it is stopped as "too many steps". From 1 to 20. | For questions that need more lookups. |
| `FIONE_LLM_TURN_TIMEOUT_SECS` | `180` | How long one answer may take, all its tool rounds included, before it ends as timed out. From 10 to 1800. | For slow models or hardware. |
| `FIONE_LLM_MAX_CONCURRENT_TURNS` | `2` | How many answers are written at once, across all users; more wait in a queue. From 1 to 16. | For a server that handles parallel requests. |
| `FIONE_MCP_ENABLED` | `false` | Serves the assistant's read-only tools over MCP at `/mcp` on Fione's own port (Streamable HTTP, JSON-RPC over POST, stateless). A client needs an API token as `Authorization: Bearer`; session cookies are refused. It can list and call the read-only tools of the projects the token's user can read, and never receives example values from a dataset. It cannot start, change or delete anything. | Set `true` to let an MCP client read your projects. |

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
| `FIONE_PUBLIC_URL` | no | Fione's origin as browsers reach it, passed to Fione (see above). |
| `FIONE_SERVING_PORT` | no | The host port of the optional `fione-serving` service (default `8081`). |
| `FIONE_MODEL_DIR` | no | The model directory the `fione-serving` service mounts (default `./model`). |
| `FIONE_LLM_BASE_URL` | no | Passed to Fione (see above). Default in Compose: the Ollama on the host, `http://host.docker.internal:11434/v1`. With the `ollama` profile: `http://ollama:11434/v1`. |
| `FIONE_LLM_PROVIDER` | no | Passed to Fione (default `ollama` in Compose). |
| `FIONE_LLM_MODEL` | no | Passed to Fione (default `gemma4:12b-mlx` in Compose; `gemma4:12b` with the `ollama` profile). |
| `FIONE_LLM_API_KEY` | no | Passed to Fione (see above). |
| `FIONE_LLM_AUTO_PULL` | no | Passed to Fione (default `false`; `true` with the `ollama` profile, which has no one to click the button). |
| `FIONE_MCP_ENABLED` | no | Passed to Fione (default `false`, see above). |

Compose refuses to start while `FIONE_S3_ACCESS_KEY` or `FIONE_S3_SECRET_KEY` is empty. The
two S3 values may only use `A-Z a-z 0-9 / + = . _ -`; SeaweedFS refuses to start otherwise.

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

## Internal variables

`FIONE_JOB_DB` and `FIONE_JOB_HANDLER_MODULES` are set by Fione for its own job worker
processes. Do not set them.

## Deployment notes

### One worker process

Fione must run as **one** process with **one** uvicorn worker (the image does this). The
sign-in throttle, the upload and password-hashing limits, the one-time display of new API
tokens and the job runner all live in that process's memory. Several workers would each keep
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

### The LLM server

An answer ends by `FIONE_LLM_TURN_TIMEOUT_SECS`, counted from the moment it was asked, and soon
after the user stops it, even when the LLM server stalls. Fione then stops waiting for that
request but cannot always close it: a server that keeps sending a byte at a time holds the
request's connection until the server's own timeouts (or a restart of Fione) end it. Each such
request keeps one connection of the shared pool (about 100), so a misbehaving server can make
later answers end as timed out. Point Fione only at an LLM server you run or trust.

Ollama reports the context of a model only while it is loaded. When the model has been
unloaded (after Ollama's `OLLAMA_KEEP_ALIVE`, 5 minutes by default), Fione loads it again before
a request that needs more than 4096 tokens, and the system page's warning about a server
context below `FIONE_LLM_CONTEXT_TOKENS` shows only while the model is loaded.

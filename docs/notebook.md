# Notebooks

A notebook is JupyterLab in a container of your own, opened inside Fione's **Notebook** page.
Code there reaches your projects through `fione-sdk`, with your access rights, without a second
sign-in. Notebooks are off by default and opt-in: they add three services (the gateway, the
launcher and the notebook image) to the Compose stack, and the launcher holds the Docker
socket (see [Known limitations](known-limitations.md#notebooks)).
Japanese: [ノートブック](notebook.ja.md).

## Enable notebooks

Add the notebook values to `docker/.env` (see `docker/.env.example`). Use the address you type
in the browser for both URLs: the same host name, and the gateway's port beside Fione's:

```sh
printf 'FIONE_PUBLIC_URL=http://127.0.0.1:8080\nFIONE_NOTEBOOK_URL=http://127.0.0.1:8888\nFIONE_NOTEBOOK_LAUNCHER_SECRET=%s\n' "$(openssl rand -hex 32)" >> docker/.env
```

Then build and start with the Compose profile `notebook`:

```sh
docker compose -f docker/compose.yaml --env-file docker/.env --profile notebook build
docker compose -f docker/compose.yaml --env-file docker/.env --profile notebook up -d
```

The build makes the notebook image (about 950 MB; 947 MB measured on arm64) and the
launcher. The launcher never pulls an image: when the notebook image is missing, starting a
notebook says "The notebook image is not installed". Without `--profile notebook` the stack
runs as before, without notebooks, and the **Notebook** link does not appear while
`FIONE_NOTEBOOK_URL` is empty. Once the notebook values are in `docker/.env`, give every Compose command
(`build`, `up`, `down`) `--profile notebook`: without it Compose leaves the notebook services
alone (an upgrade would not rebuild their images), and a start without them makes the
**Notebook** page report that the service is not available.

Every setting is in [Configuration](configuration.md): `FIONE_PUBLIC_URL`,
`FIONE_NOTEBOOK_URL`, `FIONE_NOTEBOOK_LAUNCHER_SECRET`, `FIONE_NOTEBOOK_PORT` and
`FIONE_NOTEBOOK_MAX_LIFETIME_SECS` in `docker/.env`, and the launcher's
`FIONE_NOTEBOOK_MAX_RUNNING`.

## Where the pieces are

```
browser ──> Fione (:8080)                       the Notebook page, the API
browser ──> gateway (:8888) ──> nb-<id>         JupyterLab, one container per user
notebook ──> gateway relay ──> Fione            fione-sdk calls (not published)
Fione ──> launcher ──> Docker                   starts and removes the containers
```

- **The gateway** (`notebook-gateway`, nginx) publishes JupyterLab on its own origin, port
  8888 on `127.0.0.1`, and relays the notebooks' API calls to Fione. A notebook reaches Fione
  only through that relay, which refuses `/api/v1/auth`, `/api/v1/tokens` and `/api/v1/users`.
- **The launcher** (`notebook-launcher`) starts one container per user from a fixed spec.
  Fione never touches the Docker socket.
- **The notebook containers** sit on the Compose network `notebooks`, which is internal: they
  have no route to the internet or to Fione's own services.

### The same-site rule

Fione frames JupyterLab from its own page and signs the browser in with a one-time launch
link. JupyterLab accepts that sign-in only from a page on the **same site**, so the two origins
must differ but share a site:

- **Locally:** the same host name with another port, for example `http://127.0.0.1:8080` and
  `http://127.0.0.1:8888`. `localhost` and `127.0.0.1` are different sites: if you open Fione at
  `http://localhost:8080`, write `localhost` in both URLs, and use that address in the browser.
- **In production, behind HTTPS:** sibling subdomains of one registered domain, for example
  `https://fione.example.com` for Fione and `https://nb.fione.example.com` (or
  `https://nb.example.com`) for the gateway. Use `https` for both.

`FIONE_PUBLIC_URL` is Fione's own origin as browsers reach it. Behind a TLS proxy Fione cannot
tell its scheme, so give the `https` origin. Notebooks accept framing only from this origin.
`FIONE_NOTEBOOK_URL` is the gateway's origin. Neither has a path, and they must not be the same
origin.

For the gateway behind a reverse proxy, publish the gateway's port 8888 (`127.0.0.1` by
default) under the notebook host name, and have the proxy keep the `Host` header, allow
WebSocket upgrades (kernels use them), and not time out quiet connections early.

## Grant the permission

An administrator can always use notebooks. Anyone else needs the permission:

1. Sign in as an administrator and open the **Users** page.
2. In the **Notebook** column, choose **Allow** for the user (**Revoke** takes it back).

The change applies right away. Revoking it, resetting the user's password or changing their
role so that they no longer qualify stops their notebook and ends its API token. Users
without the permission have no **Notebook** link, and the page answers 403.

A **viewer** who is allowed notebooks runs code too, but their token only reads: the
notebook has at most the access of the user's role.

## Use a notebook

1. Open **Notebook** in the navigation and choose **Start notebook**. It usually takes under
   a minute; the page shows the progress and opens JupyterLab when it is ready.
2. Create a notebook (**File > New > Notebook**, kernel Python 3) and use `fione-sdk`:

```python
from fione_sdk import Client

fione = Client()                      # FIONE_URL and FIONE_TOKEN are already set
print(fione.projects())               # the projects you can see
```

The notebook's token is made for this notebook. It acts with your role (an administrator's
notebook acts as an **editor**), expires with the notebook, and cannot manage accounts,
tokens, Python modules, model imports or project sharing. Everything else the SDK does works:
datasets (`upload`, `read`, `preview`, `profile`), `train`, `leaderboard`, `models`,
`predict`, and `run_module` (it runs the modules that exist; uploading one needs a full
token). See the [SDK's README](../sdk/README.md)
for the full tour.

If JupyterLab ignores the first Shift+Enter in a fresh notebook, run the cell again. Stock
JupyterLab does this too.

Administrators also get a Terminal in JupyterLab; other users do not.

### Using the SDK outside the UI

`fione-sdk` also runs in your own Jupyter or in a script. Install it, then give it the
address of Fione and an API token (create one on the **Account** page):

```sh
pip install ./sdk
export FIONE_URL=http://127.0.0.1:8080
export FIONE_TOKEN=fione_...
```

`Client()` then reads both; `Client(url=..., token=...)` takes them as arguments. A token
made on the Account page has your full role and does not expire unless you revoke it.

## Limits

Each notebook container gets:

| | |
|---|---|
| CPU | 2 |
| Memory | 4 GiB (no swap) |
| Processes | 512 |
| Capabilities | none; `no-new-privileges` |
| Network | internal: no internet, no Fione but through the relay |
| Files | the user's own volume |

- **Running notebooks** are capped at `FIONE_NOTEBOOK_MAX_RUNNING` (default 4) for all users
  together; another start says that too many notebooks are running. Each one may use 2 CPUs and
  4 GiB, so size the host for the number you allow.
- **Culling:** a kernel idle for 30 minutes is stopped (checked every 5 minutes), and a notebook
  with no running kernel and no activity for 1 hour shuts down, which removes its container.
- **Lifetime:** a notebook ends after `FIONE_NOTEBOOK_MAX_LIFETIME_SECS` (default 12 hours)
  whatever it is doing; its API token ends with it. Start it again from the page.
- **No egress:** code cannot download anything, so `pip install` does not work. The libraries
  are those of the image: JupyterLab, pandas, pyarrow, scikit-learn, matplotlib, httpx and
  `fione-sdk`.

## Files and persistence

Each user has a named volume, `<project>-nb-home-<user id>` (the Compose project is `fione`),
mounted at the notebook's work directory. Stopping a notebook, culling and the lifetime keep it.
**Running kernels are not kept**: they are lost when the notebook stops and when the launcher
restarts. Saved notebooks and files are kept, but a notebook's trust signatures are held in
memory, so after a restart the outputs of notebooks saved earlier show as untrusted until you
run them again.

JupyterLab's settings and layout are not saved: the gateway refuses its settings and workspace
writes, so a changed theme or panel layout is not kept.

`docker compose ... down` stops the launcher, and the launcher removes its project's
notebook containers when it stops (and when it starts). The volumes stay, also with `down -v`:
the launcher creates them, not Compose. To remove them, list and then remove by label:

```sh
docker volume ls -q --filter label=fione.project=fione
docker volume rm $(docker volume ls -q --filter label=fione.project=fione)
```

Add `--filter label=fione.uid=<user id>` to select one user's volume. A volume that a running
notebook uses is refused; stop the notebook first.

The volumes also outlive `down -v`, which resets Fione's database and with it the user ids: a
new user 2 would get the old user 2's files. After `down -v` (or any fresh `fione-data`), remove
the notebook volumes with the commands above before creating users.

Deleting a user in Fione also removes their notebook and its volume. If the launcher is
unreachable at that moment, the volume remains: Fione reuses user ids, and a later user with the
same id would see the files, so remove it with the commands above before creating more users.

## Stopping

**Stop notebook** on the page removes the container, ends the notebook's API token and keeps
the files. With JupyterLab open, the browser's console may show errors from the requests that
the stop cuts off (502, "Failed to fetch"); they are harmless.

See [Known limitations](known-limitations.md#notebooks) for what notebooks do not protect
against, and the open decision about the shared notebook origin.

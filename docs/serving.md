# Fione Serving

Fione Serving is a small prediction API for one trained model. You download the model from
Fione as a *serving bundle* (a zip), unpack it and run the `fione-serving` image on it. The
image is the same for every model; the bundle holds only the model files.

## Get the image

The image is built from this repository (no image is published yet). It must be built with
the **same `FIONE_IMAGE_TAG` as the `fione` image** that trained the model, because a model
records that tag and the serving image refuses models of another tag.

With Docker Compose, from the repository root (the tag comes from `docker/.env`, default
`dev`):

```sh
docker compose -f docker/compose.yaml --env-file docker/.env --profile serving build fione-serving
```

Or with plain Docker:

```sh
docker build -f docker/Dockerfile.serving --build-arg FIONE_IMAGE_TAG=dev \
    -t ghcr.io/codelibs/fione-serving:dev .
```

The image is about 1.7 GB: it carries the same machine-learning libraries as Fione.

## Run a model

On the model's **Prediction summary** page, the *Serve it from your own system* card offers
**Download the serving bundle** and shows the command to run. For a model trained by an image
tagged `dev` it reads:

```sh
docker run --rm -p 8081:8080 -v "$PWD/model:/model:ro" ghcr.io/codelibs/fione-serving:dev
```

Run it where you unpacked the bundle: the zip holds a `model/` directory with
`manifest.json` and `model.joblib`.

```sh
unzip fione-serving-*.zip
docker run --rm -p 8081:8080 -v "$PWD/model:/model:ro" ghcr.io/codelibs/fione-serving:dev
```

The API listens on port 8080 in the container (`-p 8081:8080` publishes it on 8081). The
process runs as a non-root user and only reads `/model`. If the model cannot be served, the
container prints one line and exits with status 1, for example:

```text
ERROR: the model in /model was made for image tag 'dev', but this image is tag '9.9'; run it with the image tagged dev
```

The same bundle and command are available from the API: `GET /api/v1/models/{id}/serving`
(the zip) and `GET /api/v1/models/{id}/serving/info` (the command and an example `curl`).

## API

Responses are JSON. Request bodies need no particular `Content-Type`.

### `POST /invocations`

Predicts each instance. The request is `{"instances": [...]}`, one object per row with a value
for every input column; extra keys are ignored.

```sh
curl -s -X POST localhost:8081/invocations -H 'Content-Type: application/json' -d '{"instances":[
  {"sepal length (cm)":5.1,"sepal width (cm)":3.5,"petal length (cm)":1.4,"petal width (cm)":0.2},
  {"sepal length (cm)":6.3,"sepal width (cm)":3.3,"petal length (cm)":6.0}]}'
```

The response has one prediction per instance, in order. A row that cannot be predicted gets
`{"exception": "..."}` and does not fail the others. From a real run with an iris model:

```json
{"predictions":[
  {"label":"setosa","index":0,"class_probabilities":[0.9934803442259019,0.003455065889847104,0.0030645898842508773]},
  {"exception":"missing columns: ['petal width (cm)']"}]}
```

- Classification (two or more classes): `label` (the predicted class), `index` (its position
  in the class list of `GET /model`) and `class_probabilities` (in that order).
- Regression: `{"value": 12.3}`.
- A number column given text that is not a number, a missing column or a row that is not an
  object: `{"exception": "..."}` for that row.

Whole-request errors answer `{"error": "..."}`: status 400 for a body that is not JSON (or
holds `NaN`/`Infinity`) or has no `instances` list, 413 for a body over 10 MiB or more than
10,000 instances. Both limits can be changed (see below).

### `GET /model`

What the model expects and predicts. From the same iris model:

```json
{"names":["sepal length (cm)","sepal width (cm)","petal length (cm)","petal width (cm)","species"],
 "domains":[null,null,null,null,["setosa","versicolor","virginica"]],
 "responseColumn":"species","category":"Multinomial","nclasses":3,"nfeatures":4,
 "uuid":"bae3b2e75a8474233aab6ce1ad9163b8",
 "instance":{"sepal length (cm)":"?","sepal width (cm)":"?","petal length (cm)":"?","petal width (cm)":"?"},
 "engine":"fione","fioneVersion":"2.0.0.dev0"}
```

| Field | Meaning |
|---|---|
| `names` | The input columns, then the column to predict. |
| `domains` | Per name, the known categories of a category column (`null` for numbers, or for more than 1,000 categories); last, the classes (`null` for regression). |
| `responseColumn` | The column to predict. |
| `category` | `Binomial` (two classes), `Multinomial` (more) or `Regression`. |
| `nclasses` | The number of classes (`1` for regression). |
| `nfeatures` | The number of input columns. |
| `uuid` | The first 32 hex digits of the model file's SHA-256. |
| `instance` | A template request row. |
| `engine`, `fioneVersion` | `fione` and the Fione version that trained the model. |

### `GET /ping` and `GET /`

An empty `200` response while the server runs. The image's Docker health check uses it. (There
is no `/health` endpoint on Fione Serving; `/api/v1/health` belongs to the Fione server.)

## Differences from v1 Fione Serving

v1 shipped a zip with a Dockerfile, `fione-serving.jar` and an H2O MOJO model that you built
with `docker build`. v2 ships only the model files; the image is shared and run with
`docker run`.

`/invocations` and `/ping` keep v1's shapes. `GET /model` keeps `names`, `domains`,
`responseColumn`, `category`, `nclasses`, `nfeatures`, `uuid` and `instance`. Compared with
v1 Fione Serving (`codelibs/fione-serving`):

- **Dropped** (H2O MOJO details with no meaning for Fione's models): `offsetColumn`,
  `algoName`, `h2oVersion`, `supervised`, `balanceClasses`, `defaultThreshold`,
  `priorClassDistrib`, `modelClassDistrib`, `mojo_version`, `modelDescriptor`.
- **Added**: `engine`, `fioneVersion`.
- **Changed**: `uuid` is now derived from the model file's SHA-256.
- v1 required `Content-Type: application/json` on `/model` and `/invocations`; v2 does not.

## Model files and trust

A model is `model.joblib` (a joblib pickle of Fione's model classes) plus `manifest.json`
(the image tag, the Fione version, the task, the target and the SHA-256 of each file). Inside
Fione the manifest is also signed with the install's secret key, and Fione only loads models
whose signature verifies.

Fione Serving cannot check that signature (it has no secret). It checks that the image tag
matches and that every file matches its recorded SHA-256, then unpickles the model. **Loading
a pickle runs code**: only serve bundles you downloaded from your own Fione. The same applies
to model imports in Fione, which only administrators can do: importing a file that was not
signed by this install needs the explicit *trust* option, which means "I vouch for this
file"; the model is then shown as of unverified origin.

## Settings of the serving image

| Variable | Default | What it does |
|---|---|---|
| `FIONE_MODEL_DIR` | `/model` | The model directory. |
| `FIONE_IMAGE_TAG` | the image's tag | Must equal the model's tag (set at build time). |
| `FIONE_SERVING_MAX_BODY` | `10485760` | The largest request body in bytes. |
| `FIONE_SERVING_MAX_INSTANCES` | `10000` | The most instances per request. |
| `PORT` | `8080` | The port inside the container. |

One prediction runs at a time per container (the libraries use every CPU core).

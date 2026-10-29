# Quick start

From nothing to a trained model, a prediction file and a running prediction API, with Docker.

## What you need

- Docker with Compose v2 (Docker Desktop, or Docker Engine with the compose plugin).
- About 6 GB of disk space for the images and their build cache, plus room for your data.
- `git`, `openssl`, `unzip` and `curl`.
- A recent browser: Chrome or Edge 123+, Firefox 120+ or Safari 17.5+ (older ones get the
  light theme only).

The images are built on your machine from this repository, on amd64 or arm64 (Apple silicon).

## 1. Get Fione and set its secrets

```sh
git clone https://github.com/codelibs/fione.git
cd fione
printf 'FIONE_S3_ACCESS_KEY=%s\nFIONE_S3_SECRET_KEY=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 32)" > docker/.env
```

`docker/.env` holds the credentials Fione and its storage (SeaweedFS) share. It is ignored by
git; keep it private. `docker/.env.example` lists the other optional values (see
[Configuration](configuration.md)).

## 2. Start it

```sh
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
```

The first build downloads and installs the machine-learning libraries and takes a few
minutes. `--wait` returns when both containers are healthy. Fione is then at
<http://127.0.0.1:8080/> (this machine only; see [Configuration](configuration.md#behind-a-reverse-proxy)
to serve others).

## 3. Create the administrator

Fione has no default password. Until an administrator exists, it writes a setup token to its
log at every start:

```sh
docker compose -f docker/compose.yaml --env-file docker/.env logs fione | grep "Setup token"
```

Open <http://127.0.0.1:8080/>. The page **Create the administrator account** asks for the
**Setup token**, an **Administrator username** and a **Password** (8 characters or more,
twice). Press **Create administrator**; you are signed in.

Do this soon after the first start: until an administrator exists, anyone who can read the
log can do it.

## 4. Get a CSV to try

Any CSV with a header row works. To try with the classic iris flowers, export the copy that
ships with scikit-learn from the running container:

```sh
docker compose -f docker/compose.yaml --env-file docker/.env exec -T fione python -c "from sklearn.datasets import load_iris; d = load_iris(as_frame=True); f = d.frame; f['species'] = d.target_names[f.pop('target')]; f.to_csv('/dev/stdout', index=False)" > iris.csv
```

This writes `iris.csv`: 150 rows, four measurements and the `species` column.

## 5. Train a model (EasyML)

1. On **Projects**, type a name under **New project** (for example `Iris`) and press
   **Create project**. Open the project.
2. Press **Upload training data**, choose `iris.csv` and press **Upload and analyze**.
3. **Data analysis** shows each column. Fione suggests the column to predict
   (**What do you want to predict?**: `species`), the **Prediction type** (classification) and
   which columns to learn from. Columns that would only leak the answer or identify rows are
   unchecked, with the reason.
4. Under **Maximum run time** choose **1 min**, then press **Run**.
5. The progress page shows what is being tried. When training ends, the
   **Prediction summary** opens: the best model, a rating from 1 to 5 stars, what the score
   means in plain words, and Fione-kun's comment.

## 6. Make predictions

On the summary, press **Make predictions**, choose a CSV with the same input columns (the
column to predict is not needed; `iris.csv` works) and press **Upload**. Then choose the
columns to keep next to the prediction and press **Predict**. The result page shows the first rows and offers the file,
`predict_<name>.csv`, with a `predict` column (the predicted class) and one `p_<class>`
probability column per class.

## 7. Serve the model

The summary's card *Serve it from your own system* offers **Download the serving bundle** and
shows a `docker run` command. Build the serving image once (it is built with the same tag as
Fione, which the model requires):

```sh
docker compose -f docker/compose.yaml --env-file docker/.env --profile serving build fione-serving
```

Then, in the directory where you downloaded the bundle:

```sh
unzip fione-serving-*.zip
docker run --rm -p 8081:8080 -v "$PWD/model:/model:ro" ghcr.io/codelibs/fione-serving:dev
```

In another terminal:

```sh
curl -s -X POST localhost:8081/invocations -H 'Content-Type: application/json' -d '{"instances":[{"sepal length (cm)":5.1,"sepal width (cm)":3.5,"petal length (cm)":1.4,"petal width (cm)":0.2}]}'
```

```json
{"predictions":[{"label":"setosa","index":0,"class_probabilities":[0.9934803442259019,0.003455065889847104,0.0030645898842508773]}]}
```

Press Ctrl+C to stop it. The prediction API has no authentication, and `-p 8081:8080` opens it on
every network interface of this machine; to keep it on this machine only, use
`-p 127.0.0.1:8081:8080`. See [Fione Serving](serving.md) for the API.

## Beyond the wizard

Choose **View: Detailed** in the account menu (your name, top right) for the AutoML screens: every
column's statistics and charts, the full training settings, the job list, the models with
their leaderboard, variable importance and score history, model export and import, and
project sharing. Administrators also manage users, Python modules and the system status from
that menu.

## Stop, back up, upgrade

Stop (the data stays in the Docker volumes `fione_fione-data` and `fione_seaweed-data`):

```sh
docker compose -f docker/compose.yaml --env-file docker/.env down
```

`down -v` would delete the volumes, and with them every project, model and user.

Back up while it is stopped, into two archives in the current directory:

```sh
docker run --rm -u 0 -v fione_fione-data:/data:ro --entrypoint tar ghcr.io/codelibs/fione:dev czf - -C /data . > fione-data.tgz
docker run --rm -u 0 -v fione_seaweed-data:/data:ro --entrypoint tar ghcr.io/codelibs/fione:dev czf - -C /data . > seaweed-data.tgz
```

`fione-data.tgz` holds the database and the secret key: keep it private. `docker/.env` is not
in the archives; keep it with them, or create a new one with the `printf` command of step 1.

To restore into empty volumes (for example on a new machine, before the first start), build
the images, restore, then start as usual (Compose warns that the volumes already exist; that
is expected):

```sh
docker compose -f docker/compose.yaml --env-file docker/.env build
docker run --rm -i -u 0 -v fione_fione-data:/data --entrypoint tar ghcr.io/codelibs/fione:dev xzf - -C /data < fione-data.tgz
docker run --rm -i -u 0 -v fione_seaweed-data:/data --entrypoint tar ghcr.io/codelibs/fione:dev xzf - -C /data < seaweed-data.tgz
```

To upgrade, back up, keep the current serving image under another name (the rebuild
replaces `ghcr.io/codelibs/fione-serving:dev`), then get the new version and rebuild:

```sh
docker tag ghcr.io/codelibs/fione-serving:dev fione-serving:before-upgrade
git pull
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
```

The data stays. Models trained by an older version are not guaranteed to load in a newer one
(they are pickles of Fione's code), so retrain the models you rely on after an upgrade. Until
then, serve their bundles with the kept image: replace `ghcr.io/codelibs/fione-serving:dev`
with `fione-serving:before-upgrade` in the `docker run` command. (Setting a different
`FIONE_IMAGE_TAG` in `docker/.env` for each version avoids this: both images then carry the
version in their tag.)

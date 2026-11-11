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
   which columns to learn from. Columns that are a copy of the answer, or whose value decides
   it, and columns that only identify rows are unchecked, with the reason. A column that only
   predicts the answer suspiciously well stays checked, with a warning: check that its value is
   known when you make predictions. Above it, the Assistant comments on the data in plain
   words and may propose a training you can start with one button.
4. Under **Maximum run time** choose **1 min**, then press **Run**.
5. The progress page shows what is being tried. When training ends, the
   **Prediction summary** opens: the best model, a rating from 1 to 5 stars, what the score
   means in plain words, and a short comment from the Assistant.

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
column's statistics and charts, the full training settings (which start with the run time
recommended for the size of the data and show the same warnings and tips as **Data analysis**),
the job list, the models with their leaderboard, variable importance and score history, model
export and import, and project sharing. Administrators also manage users, Python modules and the
system status from that menu.

To drive Fione from Python, use `fione-sdk` (see [sdk/README.md](../sdk/README.md)). To ask
questions about your data and models in plain language, use [the assistant](assistant.md)
(it needs a language model: Ollama or Claude).

## Choosing the score

"Ranking metric" orders the leaderboard; "Stopping metric" decides whether a try improved
(`sort_metric` and `stopping_metric` in the API; *Automatic* is log loss for classification and
RMSE for regression). The models are always trained on log loss or squared error, and so are the
weights of the final blend: the metric ranks the models, stops the search and is reported, and
every metric that fits the data is listed on the model's Metrics tab, in the target's own units.

- Classification: log loss, AUC, accuracy, average precision (`aucpr`), Gini, lift of the top 10%
  (`lift_top_group`), balanced accuracy, error rate (`misclassification`), mean error per class
  (`mean_per_class_error`), F1, precision, recall, MCC, kappa, quadratic weighted kappa (`qwk`),
  Brier score, top-3 accuracy (`top3_accuracy`) and MAP@3 (`map3`).
- Regression: RMSE, MAE, R², MSE, RMSLE, MAPE, SMAPE, median absolute error (`medae`), explained
  variance, correlation (`pearson`), rank correlation (`spearman`), normalized Gini
  (`normalized_gini`), Poisson deviance (`poisson`) and quadratic weighted kappa of the rounded
  predictions (`rounded_qwk`).

When you name no metric, EasyML and the assistant's proposal rank by average precision (`aucpr`)
for two classes with a rare one (under 10% of the rows), and the engine's *Automatic* is log loss
or RMSE otherwise. Name the score your goal uses (a metric the task fixes, say) in the training
settings, in the API, or to the assistant, which can set it in its proposal.

Metrics that count right answers (accuracy, F1, kappa, ...) use the predicted class described
below; with more than two classes precision, recall and F1 are the mean over the classes, and with
two classes they describe the class listed last. The ranking measures (AUC, average precision,
Gini, lift) are reported for two classes only. Kappa and `qwk` take the classes in their sorted
order, so `qwk` suits ratings. RMSLE, Poisson deviance and normalized Gini need target values of
0 or more, MAPE needs values other than 0, `rounded_qwk` needs whole numbers, and top-3 accuracy
needs more than three classes and MAP@3 three or more; training stops with an error when the target does not fit.

## Choosing the predicted class

A classification model predicts the class with the largest probability. When one class is much
rarer than the others and the score treats every class alike (balanced accuracy, macro recall),
set "Choosing the predicted class" to *Adjust for class sizes* (`decision: "balanced"` in the
API). The predicted label is then the class whose probability is largest relative to its share of
the training data, so rare classes are predicted more often. The probabilities do not change;
the accuracy and the confusion matrix of the training result, batch prediction, Fione Serving
and the explanation follow the same rule. It cannot be combined with "Balance the classes",
which corrects the same imbalance while learning, and it is ignored for regression.

For two classes scored by a metric that counts right answers, *Fit to the ranking metric*
(`decision: "tuned"`) picks the probability threshold that gives that metric its best value on the
validation predictions, instead of 0.5; the ranking metric must be one of accuracy, error rate,
balanced accuracy, mean error per class, F1, MCC, kappa or `qwk` (precision and recall alone would
be best served by predicting almost nothing or almost everything). The threshold is stored with
the model and used by predictions, Fione Serving and the explanation; the probabilities do not
change, and the leaderboard scores each row at its own best threshold. The threshold is chosen on
the same validation predictions the scores are reported on, so those scores are somewhat
optimistic, most with few rows or few cases of the rare class. The stopping metric, and the
ensemble's progress scores while training, are evaluated at 0.5.

For ordered classes (a rating of 0 to 4, an adoption speed) scored by `qwk`, the class with the
largest probability is a poor answer: it is far from the truth more often than the middle one.
With `decision: "tuned"` and `sort_metric: "qwk"`, for up to 50 classes in the order of their
labels, Fione takes each row's expected class number (the probabilities times the class numbers)
and fits cut points on it, on the validation predictions, that give the best `qwk`; a row is the
class its expected number falls in. The cut points are stored with the model and used like the
threshold above; without `tuned`, a `qwk` run says in a notice that it would score better with
them.

## Text columns

A column of running text (the median value has five words or more, or three or more in values that are mostly different, such as the title of a product) is read in two ways. Its
topics are derived features (see below). A model family called TextLinear also reads its words:
a logistic (or ridge) regression on the TF-IDF weights of words and word pairs, with the other
columns beside them, learned again on each training fold. It joins the search and the ensemble
only for data with such a column, and its predictions are mixed with the other families' by the
same cross-validation scores.

Three variants of it are *late candidates*: TextLinearWide (up to 100,000 words and word pairs
per column), TextLinearChar (the words and also the character n-grams of 2 to 5 letters; it is
left out when the text is very large or has no spaces) and TextLinearPlain (without the derived features; it is
tried only when derived features were added). They run after all the other families, in the
search time that is left: for text data, 15% of the search time is kept for them (taken from
the other families, not from TextLinear), and what the other families leave unused is added. Each takes a share of that time, and one that cannot finish
a first trial in its share is skipped. A late candidate stays in the model
only when its cross-validation scores improve the ensemble; otherwise it gets weight 0 and is
dropped. They are not run for data without a text column.

## Values from earlier times

For data over time, the value of a column at an earlier time is often the best feature (last
month's sales of the same shop and item). The built-in **Add values from earlier times**
module (`lag`) adds them: name the `time` column (whole numbers such as a month number, or dates,
where a step is a day; text must be written year-month-day, such as `2015-07-01`; for times that
are not whole numbers, such as readings every 0.0001, or dates a week apart, set `step` to the gap
between neighbouring times, 0.0001 or 7, and every time must be a whole number of steps from the
others), the columns to
read (`columns`), the group each row belongs to (`by`, such as a shop and an item) and
the steps back (`lags`, such as `1,2,3,12`). `sales_lag3` is the value of `sales` three steps of
the time before, so a time with no row gives an empty value, never the row before. The rows of
a group at one time are reduced to their mean (or sum, with `how`) first, so a coarser `by`
gives, for example, the mean of an item over all its shops one month earlier. No row reads its
own time or a later one, but the module does not know which rows are to be predicted: to give
the rows to predict their lags, put them in the same dataset (with the target empty) before
adding the lags. Training refuses a target with missing values, so take the rows to learn from
with **Slice rows** (such as `month < 34`) before training, and the rows to predict with another
slice for the prediction.

## Statistics of nearby values

For a signal or a sensor, the rows next to a row often say more than the row: a level that
the readings around it stay near, how much they spread. The built-in **Add statistics of nearby
values** module (`rolling`) adds them: name the `order` column (numbers, or dates such as
`2015-07-01`; text must be a date written year-month-day), the columns to read (`columns`),
the group each row belongs to (`by`, such as a machine), the `window` (a number of rows) or the `span`
(a range of the order, such as 0.0005, or a number of days for dates; name one of the two) and
the statistics (`stats`: `mean`, `std`, `min`, `max`, separated by commas). A `span` makes a row
read the rows within that range, so a gap in the readings gives a shorter window instead of
one that reaches further back. The rows are taken
in the order of the `order` column, whatever order they are in the file. With `side` set to
`before` (the default), `signal_before5_mean` is the mean of the 5 rows before the row: only
rows whose order is earlier than the row's, so the row itself, later rows and rows with the
same order (several rows of one day) are never read. With `around`, `signal_around5_std` is the
standard deviation of the 5 rows centred on the row, itself included (the window must be odd);
it reads later rows and rows with the same order, so use it only on columns whose later values
are also known when the model is used, never on the target. With a `span`, `before` reads the
rows within the span before the row and `around` the rows within half of the span either side of
it, itself included. A window at the edge of a group is shorter, a `std` needs at least two
values, and an infinite value counts as missing. A row with no `order` or no `by` value gets
empty values and is left out of the windows of the others.

## Learning a skewed target

For a regression target of 0 or more that is skewed (prices, counts, durations) and is
scored by relative error such as RMSLE, set "Learning the target" to *Logarithm*
(`target_transform: "log1p"` in the API). Fione then learns log(1 + value) and gives predictions
in the column's own units again. The model's scores, the diagnostics, the leaderboard, batch
prediction, Fione Serving and the explanations are all in those units; the explanation shares the
change from the bias to the prediction in proportion to each column's effect on the logarithm,
which is an approximation. Only the scores of the search itself (the trial history) stay on the
logarithm scale. Every value must be above -1, and the setting is ignored for classification.

## Data that follows time

When the rows to predict come after the rows to learn from (sales of next month, a later
period of a market), shuffled cross-validation parts overstate the score: a model learns from
days after the ones it predicts. Choose a column that orders the rows in time ("Order of the
rows in time", `time_column` in the API; a number, a date, or text a date can be read from, with
no missing value). Fione then cuts the rows, in the order of that column, into `nfolds` + 1 parts of
about the same size. Fold *j* checks the models on part *j* and learns from the parts before
it, so no model learns from a later row than it predicts. Rows with the same value of the
column are in the same part, and a column with few different values gives fewer folds.

The first part is only learned from. The scores, the ensemble weights, the diagnostics and the
cross-validation predictions cover the other parts; a row of the first part has no prediction
(empty in the kept predictions, fold -1 in the fold assignment). The final models learn
from all the rows. The column can be left out of the inputs and still order the rows.
Derived features are not tried in this mode, since their check uses shuffled folds. A
classification needs every class in the earlier parts of each fold, and more than one class in
the parts that are predicted. A family that has no final refit (DeepLearning) keeps only the model
of the last fold, which learned from the most rows.

## Repeating the cross-validation

With few rows, one random split into folds is noisy: a search over many trials then picks
settings that happened to score well on that split, and the model does worse on new data than
its score says. Up to 2,000 rows Fione therefore draws the folds three times with other seeds
(twice up to 5,000 rows) and judges each trial by the mean of the repeats' scores; the ensemble
is chosen on all repeats. The models, the diagnostics, the leaderboard and the cross-validation
predictions come from the first repeat. Set "Repeats of cross-validation" (`cv_repeats` in the
API) to choose the number yourself (1 to 10); 1 turns it off. With as few groups as folds
(see below) the folds cannot differ between repeats, and folds in time order are one fixed
partition, so neither is repeated. A run of fixed length tries fewer trials the more repeats it
has.

## Keeping related rows together

Fione scores a model on rows it did not learn from, chosen at random. When several rows
belong together (the same customer, patient or store) and the data you will predict holds other
ones, a random split puts rows of one customer on both sides, and the score looks better than it
is. Choose that column as "Keep related rows together by" (`cv_group_column` in the API): the
rows with one value then always stay in the same validation fold, in the search and in the choice
of derived features alike. The column is still an input unless you leave it out. A missing value
counts as one group, and with fewer groups than folds the number of folds is lowered to the
number of groups (at least two groups are needed). A class that occurs in so few groups that
some fold's training rows lack it is refused, with the column named. The analysis page and the
assistant suggest this when a column named like an ID (`user_id`, `顧客ID`) repeats its values over rows.

A group column and a time column cannot be used together.

## Derived features

Fione builds *derived features* that never read the target, and chooses among them by
validation (the "Add derived features" option, `feature_engineering` in the API, on by default):

- text columns: the common words (letter runs, so `C85` gives `c`) as 0/1 flags, plus length,
  word count, share of digits and capitals and the first number; for running text (a median
  of five words or more, or the titles described under Text columns) also 32 *topics*, the main directions of word use found by an SVD of
  the word weights (TF-IDF);
- pairs of text columns: with two or more text columns, for each pair among three of them
  (running texts first), such as a question and its candidate duplicate or a title and a
  description: how many words they share, their share of all the words and of the shorter text,
  the difference and ratio of the word counts, and whether the first word, the last word, the
  numbers or all the words are the same;
- categories: how common each is, and how common each pair is;
- identifiers: a string column (two of them at most) with at least 12 distinct values and no
  spaces, whose values (the first 1,000 non-missing ones are judged) split by `_`, `/`, `-`, `:`
  or `.` into the same two to four fields on at least 95 % of them (`0001_01`, `B/0/P`), gets
  one feature per field, the number for a numeric field and how common the value is otherwise,
  and the number of training rows that share the first field (the size of a group). A value not
  seen in training gives a missing feature, not zero. This group is tried last;
- rows: the number of missing values and of zeros; with 10 number columns or more also the
  mean, median, maximum and standard deviation of the row's numbers that are neither zero nor
  missing, after a signed log so that columns of different scales weigh alike;
- dates: hour, minute, week, quarter, day of the year, weekend, and the seconds between date
  columns;
- numbers: sums, differences, products and ratios of the few most useful number columns, their
  means within each of the three most useful small categories (and the difference from it),
  how common each repeated value is, and k-means clusters with the distance to the cluster
  centre.

Date features need a column of dates. ISO dates are detected on upload; a column of other date
strings (`25-12-2024 09:00`, `Mar 5, 2024`) is recognised when a model is trained, and its
dates are read with the day first when some first field is above 12 and no second field is
(`02-10-2012` is then the 2nd of October), otherwise with the month first. Independently of
this option, the linear model and the neural network log-transform non-negative numbers
that are strongly skewed.

Each group is tried on a small LightGBM over rows it samples, and kept only if the loss drops
over paired cross-validation folds by more than three standard errors and by 0.1 % on average,
with at least 70 % of the folds improving, and the kept groups together pass a last check on
other folds of the same rows. The gate gets a tenth of the run time (a short run gives it 30 seconds, but never more than 30 % of the run). The groups tried,
their gains and why each was kept or not are on the model (`features`) and in a `features`
notice.

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

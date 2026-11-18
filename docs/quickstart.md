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

A training run also says when its validated score is suspicious: an R-squared of 0.999 or more
(or an AUC of 0.9995 or more for two classes) usually means a column gives the answer away and
will not be known when the model is used, and an R-squared of 0.02 or less (or an AUC of 0.55 or
less) means the model is hardly better than the average.

"Ranking metric" orders the leaderboard; "Stopping metric" decides whether a try improved
(`sort_metric` and `stopping_metric` in the API; *Automatic* is log loss for classification and
RMSE for regression). The models are trained on log loss or squared error, and so are the
weights of the final blend, except that for a regression ranking metric of `mae`, `medae`,
`smape`, `rmsle`, `poisson` or a relative error the blend picks its weights by that metric,
in the target's own units, so that the ensemble is never worse on it than its best model. The
metric ranks the models, stops the search and is reported, and
every metric that fits the data is listed on the model's Metrics tab, in the target's own units.
A relative error (`mape`, `rmspe`) goes further: each row then counts by its share of
that error (weight 1 / |y| or 1 / y², capped at the 99th percentile; with `target_transform`
`log1p`, the weight allows for the log), in the training and in the blend, so the models fit the
small targets as closely as the large ones.

- Classification: log loss, AUC, accuracy, average precision (`aucpr`), Gini, lift of the top 10%
  (`lift_top_group`), balanced accuracy, error rate (`misclassification`), mean error per class
  (`mean_per_class_error`), F1, macro F1 (`macro_f1`), precision, recall, MCC, kappa, quadratic weighted kappa (`qwk`),
  Brier score, balanced log loss (`balanced_logloss`), top-3 accuracy (`top3_accuracy`) and MAP@3
  (`map3`).
- Regression: RMSE, MAE, R², MSE, RMSLE, MAPE, RMSPE, SMAPE, median absolute error (`medae`), explained
  variance, correlation (`pearson`), rank correlation (`spearman`), normalized Gini
  (`normalized_gini`), Poisson deviance (`poisson`), quadratic weighted kappa of the rounded
  predictions (`rounded_qwk`), for a quantile (see below), the pinball loss (`pinball`) and, for a
  time that may be cut short (see below), the concordance (`concordance`).

`balanced_logloss` is the log loss of a task whose classes count alike, however rare one is: each
class's mean log loss, averaged. It is measured on the probabilities shifted so that every class
is as common as the others, and a model ranked by it delivers those probabilities (and the label
that is the largest of them), so the score on its page is the score of what it predicts.

When you name no metric, EasyML and the assistant's proposal rank by average precision (`aucpr`)
for two classes with a rare one (under 10% of the rows), and the engine's *Automatic* is log loss
or RMSE otherwise. Name the score your goal uses (a metric the task fixes, say) in the training
settings, in the API, or to the assistant, which can set it in its proposal.

Metrics that count right answers (accuracy, F1, kappa, ...) use the predicted class described
below; with more than two classes precision, recall and F1 are the mean over the classes, and with
two classes they describe the class listed last. The ranking measures (AUC, average precision,
Gini, lift) are reported for two classes only. Kappa and `qwk` take the classes in their sorted
order, so `qwk` suits ratings. RMSLE, Poisson deviance and normalized Gini need target values of
0 or more, MAPE and RMSPE need values other than 0, `rounded_qwk` needs whole numbers, and top-3 accuracy
needs more than three classes and MAP@3 three or more; training stops with an error when the target does not fit.

With `rounded_qwk` on whole-number ratings (three to fifty different ones), the cut points that
turn a prediction into a rating are fitted to the order of the ratings, on the final blend's
out-of-fold predictions, instead of rounding at the middles between whole numbers: a model that
predicts the middle ratings too often gets its rare high ratings back. The reported value counts
the ratings at those cut points (it is a little optimistic, as the cut points were fitted on the
same predictions), and `predict` returns the rating they give, not the fraction. The cut points
are part of the model: do not apply them again to its predictions. `keep_cv_predictions` keeps the
blend's fractions, before the cut points.

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
balanced accuracy, mean error per class, F1, macro F1, MCC, kappa or `qwk` (precision and recall
alone would be best served by predicting almost nothing or almost everything). For two classes F1 is that of the
class listed last, which for a common class rewards predicting it for almost every row; macro F1
averages the F1 of both classes (for more classes F1 is already that average). The threshold is stored with
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

A column of running text (the median value has five words or more, or three or more in values that are mostly different, such as the title of a product, or that take a thousand different values or more, such as a search query) is read in two ways. Its
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

## Data with one column per time

Sales kept as one column per day (`d_1`, `d_2`, ...) have a column for every time and no column
for the time itself. The built-in **Unpivot columns into rows** module (`unpivot`) turns them into
rows: name the columns to keep as they are (`keep`, such as the item and the shop), and every
other column (or only those named in `columns`, when it is not all of them) becomes one row per
original row, with the column's name in the new column that `name` names (`variable` by default) and its
value in the one that `value` names (`value` by default). Add the time of each day with **Join datasets by key columns**
before using **Add values from earlier times**.

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
gives, for example, the mean of an item over all its shops one month earlier. A lag that comes out empty on nearly every row is reported (months written as dates are not
a step of one apart). No row reads its
own time or a later one, but the module does not know which rows are to be predicted: to give
the rows to predict their lags, put them in the same dataset (with the target empty) before
adding the lags. Training refuses a target with missing values, so take the rows to learn from
with **Slice rows** (such as `month < 34`, or `sales is not empty` for the rows where `sales`
has a value; `is empty` selects the others) before training, and the rows to predict with
another slice for the prediction. A lag cannot reach beyond the end of the history, so rows to predict
that lie further ahead than the lag have it empty: a prediction run reports the columns that
the model learned from filled in and the rows to predict mostly lack, and a model that leans on
them is not to be trusted.

A table of things followed over time (a column of at least 20 values, each on 5 rows or more,
seen once at each time of a date column or of the `time_column`) whose target follows its own
value at the previous time (correlation 0.7 or more once the mean of each thing and of each time
are taken off) while no numeric column tells the target at least 0.8 of that well gets a notice:
the model sees each row alone, and the module above adds what the same thing did earlier. A thing
named by several columns together (a shop and an item), a time that is not a date or the
`time_column`, a table of over 200 columns, a classification, a quantile and a survival fit get
none.

## Statistics of nearby values

For a signal or a sensor, the rows next to a row often say more than the row: a level that
the readings around it stay near, how much they spread. The built-in **Add statistics of nearby
values** module (`rolling`) adds them: name the `order` column (numbers, or dates such as
`2015-07-01`; text must be a date written year-month-day), the columns to read (`columns`),
the group each row belongs to (`by`, such as a machine), the `window` (a number of rows) or the `span`
(a range of the order, such as 0.0005, or a number of days for dates; name one of the two) and
the statistics (`stats`: `mean`, `std`, `min`, `max`, `sum`, `count`, separated by commas). A `span` makes a row
read the rows within that range, so a gap in the readings gives a shorter window instead of
one that reaches further back. The rows are taken
in the order of the `order` column, whatever order they are in the file. With `side` set to
`before` (the default), `signal_before5_mean` is the mean of the 5 rows before the row: only
rows whose order is earlier than the row's, so the row itself, later rows and rows with the
same order (several rows of one day) are never read. With `around`, `signal_around5_std` is the
standard deviation of the 5 rows centred on the row, itself included (the window must be odd);
it reads later rows and rows with the same order, so use it only on columns whose later values
are also known when the model is used, never on the target. With `after`, `signal_after5_mean` is
the mean of the 5 rows after the row: only rows whose order is later than the row's, so the row
itself, earlier rows and rows with the same order are never read; the same caution applies, and
next to a `before` window it shows what changes at a row (a level that drops or rises). With a
`span`, `before` reads the rows within the span before the row, `after` the rows within the span
after it, and `around` the rows within half of the span either side of it, itself included. A window at the edge of a group is shorter, a `std` needs at least two
values, and an infinite value counts as missing. A row with no `order` or no `by` value gets
empty values and is left out of the windows of the others. A `window` wider than any group
(up to 1,000,000 rows) makes `before` read every earlier row of the group, so `sum` gives a
running total (`signal_before1000000_sum`) and `count` the number of earlier rows that hold a
value; a row with no earlier row, or none that holds a value, stays empty.

## The rank within a group

A value is often meaningful only against the others of its group: a player's damage compared
with the rest of the match. The built-in **Add the rank within a group** module (`rank`) adds
one column, `column_rank`: name the numeric `column` and the group each row belongs to (`by`;
all rows form one group if it is empty). The rank is the number of values in the group that are
smaller than the row's value, plus one, divided by the number of values in the group, so the
smallest is 1/n, the largest is 1, and tied values share the lowest rank of the tie (a
group of one gets 1). With `how` set to `dense`, `column_dense_rank` is 1 for the smallest
value, 2 for the next one above it, and so on, tied values sharing a rank. With `among` (a column
inside each `by` group, such as the team inside a match), each `among` group is first reduced to the mean of `column`, and the rank is that of the group's mean among the
groups of its `by` group, so every row of a team gets its team's rank in the match. A row with no value
(or no `by` or `among` value) gets an empty rank and is left out of the others' ranks. The rank is computed from the rows of the dataset it is added to.

## A column computed from other columns

The built-in **Add a calculated column** module (`calc`) adds one column made from the numeric columns
of the dataset: name the new column (`name`; it must not exist yet) and write how to compute it
(`expression`, up to 1,000 characters). The other columns and the rows stay as they are, and the new
column holds decimal numbers. For example `close / close_before1_mean - 1` (a return),
`price - price_around999999_mean` (a value relative to its group's mean), `flag - flag_lag1` (a change
from the month before) or `rowsum("flag_*")` (the number of the flags `flag_...` that are set).

An expression is built from:

- numbers, and the names of columns. A name with spaces or symbols, or one that is not a plain word,
  is written `col("unit price")`. A column must be numeric (a yes/no column counts as 0 and 1).
- `+ - * / **` and parentheses (`nan` is an empty value, unless a column has that name).
- comparisons `== != < <= > >=`, which give 1 or 0 (a comparison with an empty value gives 0, and
  `!=` gives 1), and `&`, `|`, `~` for "and", "or", "not" on such values, which also give 1 or 0 (an
  empty value is false). Put each comparison in parentheses: `(a > 0) & (b > 0)`.
- `abs`, `sqrt`, `log`, `log1p`, `exp`, `min2(x, y)` and `max2(x, y)` (the smaller and larger of two
  values), `clip(x, low, high)`, `isnull(x)` (1 where `x` is empty) and `where(condition, x, y)`
  (`x` where the condition is true, `y` elsewhere).
- `rowsum`, `rowmean` and `rowcount` of any number of values on one row, which skip the empty ones:
  `rowsum(a, b, c)`, or a pattern in quotes for every column whose name matches it (`*` for any
  characters, also none; it is the only wildcard), such as `rowsum("flag_*_on")`, which gives the number
  of such flags that are set. `rowsum` of nothing but empty values is 0, `rowmean` is empty, and
  `rowcount` is the number of values that are not empty.

A result that is infinite is empty: a division by zero (`a / 0`), `log(0)` or an overflow; the job
reports how many rows had one, and an infinite value in a column counts as empty without a report.
A column that several patterns of one row function match is read once. The row functions read at most
10,000 columns and values in all, and the rows times those read is limited like the size of a result
(150 million cells). An expression also holds a number of columns of intermediate values while it
runs (a sum written `a+b+c` holds three; `-a+(-a+(...))` nested on the right holds one more for each
level), and that number plus the dataset's columns times the rows is limited the same way.

Nothing is run but this arithmetic: calls to other functions, attribute access, indexing and the
like are refused with a message, as are an unknown column or one that is not numeric. An expression can nest to about 100 levels.

## Learning a skewed target

For a regression target of 0 or more that is skewed (prices, counts, durations) and is
scored by relative error such as RMSLE, set "Learning the target" to *Logarithm*
(`target_transform: "log1p"` in the API). Fione then learns log(1 + value) and gives predictions
in the column's own units again. The model's scores, the diagnostics, the leaderboard, batch
prediction, Fione Serving and the explanations are all in those units; the explanation shares the
change from the bias to the prediction in proportion to each column's effect on the logarithm,
which is an approximation. Only the scores of the search itself (the trial history) stay on the
logarithm scale. Every value must be above -1, and the setting is ignored for classification.

A regression target with no value below 0 (a price, a count) never gets a prediction below 0:
`predict` and batch prediction raise such a prediction to 0, with or without the logarithm. The
scores of the training are those of the predictions before this, and the explanation of a row
shows the prediction it adds up to.

## Predicting a quantile

A regression predicts the mean of the target. To predict a quantile instead (the level a target stays under
nine times in ten, a lower bound, the median), set `quantile` in the API to a number
above 0 and below 1. It applies to regression only. The models then learn the pinball loss at that
level: a prediction too low counts the quantile of its miss, and one too high counts one minus the
quantile. Only LightGBM, XGBoost and CatBoost can do this, so only they are searched, and a notice
says so. The derived features are not tried.

*Automatic* ranking and stopping metrics are then the pinball loss (`pinball`, which is refused
without a quantile), the final blend picks its weights by it, and the Metrics tab lists it besides
the other metrics, which score the quantile as if it were a forecast of the mean. The loss is
measured in the target's own units, also with `target_transform` `log1p` (a quantile follows a
monotone transform). One model learns one quantile: a band between two levels is two runs. The
share of held-out rows below a model's predictions is the check to make on it: it is close to the
quantile with plenty of rows, and falls short of it in the tails (0.1 and 0.9, say) on a small
table.

## A time that may be cut short

A target that is the time until an event (a relapse, a failure, a churn) is often only known to be
at least some value for the rows where the event has not happened yet. Give a column that is 1 where
the event happened at the target's time and 0 where the row was last seen at that time
(`event_column` in the API; the target is then a regression, and the column is not a feature). The
models learn a score that grows with the time, and a prediction is that score: a higher one is a
longer time, and it is not a time in the target's units.

The score is the probability, by the Kaplan-Meier estimate of all the training rows, that the event
has happened by the row's time (a row with an event) or by the time it is expected to last (a
censored row, taken at its time plus what the estimate leaves of the time up to the last event). It
is computed once from all the rows, as a monotone curve of the times; the validation parts are the
ones the models do not learn from.

*Automatic* ranking and stopping metrics are then the concordance (`concordance`, which is refused
without an `event_column`, and the only metric an `event_column` allows): of the pairs of rows where
one has its event before the other's time (a censored row at the time of an event counts as lasting
longer), the share that the predictions order the same way, equal predictions counting half (1 is
perfect, 0.5 is chance). It is computed on the validation
predictions of all the parts together. The leaderboard and the Metrics tab report it; the other
metrics, which compare a prediction with the time, are not reported. A quantile and a
`target_transform` cannot be used with an `event_column`.

## Data that follows time

When the rows to predict come after the rows to learn from (sales of next month, a later
period of a market), shuffled cross-validation parts overstate the score: a model learns from
days after the ones it predicts. Choose a column that orders the rows in time ("Order of the
rows in time", `time_column` in the API; a number, a date, or text a date can be read from, with
no missing value). Fione then cuts the rows, in the order of that column, into `nfolds` + 1 parts of
about the same size. Fold *j* checks the models on part *j* and learns from the parts before
it, so no model learns from a later row than it predicts. Rows with the same value of the
column are in the same part, and a column with few different values gives fewer folds.
With a group column too ("Keep related rows together by"), each group is ordered by its
last row and all its rows are in one part, so no group has rows on both sides of a fold, and a
fold learns only from groups that end no later than the ones it predicts. Rows are not ordered
inside a group: an early row of a validated group is predicted from other groups' later rows.
This serves groups that sit inside a stretch of time (the rows of one search, one order, a
short visit). Groups that stay over the whole range (users present at every period of a
stacked table) all end together, so a fold learns from few rows and predicts many, and a notice
says so; with all of them ending at the same value the run is refused. For such data use the
group column alone. With fewer groups than parts the number of folds is lower, as with few
different values of the column.
When a column holds dates, or whole numbers that are dates (20141021, or 14102100 for a year,
month, day and hour) or Unix times (seconds or milliseconds between 2000 and 2100), and no time
column is given, a notice points this out, since the score
of shuffled parts is then probably better than on later dates. The models read such a whole-number
column as a number and also as its year, month, day, day of the week and, with an hour or a
Unix time, hour of the day.

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
A training run also says so when no group column is given and a text column of 100 or more
values has about 20 rows or more for each value, and the rows of one value share the value of
most other columns (rows of one game or patient look alike).

A group column and a time column can be used together (see "Data that follows time").

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
that are strongly skewed. A training run names the columns it leaves out because they hold one value, or none, on every
training row. A text column in which nearly every value is a number and a unit of
time (`2 years`, `3 weeks`, `10 days`, with at least three different values) is read by the
models as a number of days.

Each group is tried on a small LightGBM over rows it samples, and kept only if the loss drops
over paired cross-validation folds by more than three standard errors and by 0.1 % on average,
with at least 70 % of the folds improving, and the kept groups together pass a last check on
other folds of the same rows. The gate gets a tenth of the run time (a short run gives it 30 seconds, but never more than 30 % of the run); when that is not enough for every group, it stops judging in time for the last check of the groups it has kept, and the groups it did not reach are marked as not judged. The groups tried,
their gains and why each was kept or not are on the model (`features`) and in a `features`
notice. A table of more than 5,000 columns gets none: one fit of the quick model on so many
columns takes longer than the time the gate has, and a `notice` says so.

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

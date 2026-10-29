# Known limitations

What this release does not do, or does with a catch. Japanese summary at the end.

## Security and accounts

- **Sessions cannot be revoked on the server.** A session cookie is signed and holds no server
  state. Signing out deletes the cookie in that browser only; a copied cookie stays valid
  until it expires (`FIONE_SESSION_MAX_AGE_SECS`, 7 days by default). Changing a password ends
  every session of that user (sessions are bound to the password).
- **A password reset by an administrator keeps the user's API tokens.** Revoke them as well
  if the account is compromised; the user can do so on the Account page, and an administrator
  can through the API (`DELETE /api/v1/tokens/{id}`). There is no screen for an administrator
  to manage other users' tokens. Deleting the user removes their tokens, but is refused while
  they own projects or jobs.
- **Uploaded Python modules are not sandboxed.** They run in the job worker with the server's
  privileges and can read its secret key and environment. Only administrators can upload
  them, after confirming a warning. Built-in modules are not affected.
- **Replacing a module affects queued jobs.** A job that is still waiting runs the module's
  source as it is when the job starts, not as it was when the job was queued.
- **Error messages shown to non-administrators lose file paths, but not URLs or host
  names** (for example `seaweedfs:8333` in a storage error).
- **CSV downloads are not protected against spreadsheet formula injection.** A cell starting
  with `=` is written as it is; spreadsheets may evaluate it.
- **The first-administrator setup token is in the log** until an administrator exists (unless
  you set `FIONE_SETUP_TOKEN`).
- **The S3 credentials are visible** in the containers' environment (`docker inspect`,
  `docker exec`) to anyone who can use Docker on the host.
- **API tokens you create never expire**, and Fione does not record when one was last used.
  Revoke tokens you no longer need on the Account page. Notebook tokens (made for the notebook
  container) expire with it, act at most as an editor, and cannot manage accounts, tokens,
  modules, imports or sharing.
- **Fione Serving has no authentication** and no rate or concurrency limit for predictions
  (only the request size limits). Requests for contributions are capped (2 at once by default,
  then 503), but each one holds the model while it runs, so plain predictions wait for it, and
  can take about 100 MiB of memory at the largest request body. The
  command the UI shows, `docker run --rm -p 8081:8080 …`, publishes it on every network
  interface of the host; use `-p 127.0.0.1:8081:8080` to keep it on that machine, and a reverse
  proxy with authentication to serve others.
- **Imported models** that were not made by this installation load only if an administrator
  ticks the trust option on import; the model is then marked "Imported, unverified". Loading
  a model file runs code, so trust only files you know.
- **A model's diagnostics hold training values.** They keep the class labels and, for
  regression, up to 2,000 actual target values sampled from the training rows, with the
  model's predictions for them. Every reader of the project sees them (the Metrics tab and
  `GET /api/v1/models/{id}/diagnostics`), they go into the model's export, and they stay when
  the training dataset is deleted. The stored explanation likewise keeps category levels and
  class labels after the dataset is gone (it is not exported). The model file and the serving
  bundle carry no diagnostics.
- **Installs from before model diagnostics existed refuse exports that carry them**
  ("unexpected fields"). Both are version 20.0.0, so the version does not tell them apart.
- **Model imports are stricter than before.** A record with a number that is not finite or an
  integer beyond the range of a float anywhere in it, diagnostics included, or with diagnostics
  that have unknown fields or nest deeper than training writes them, is refused. Exports never
  hold such values.

## Jobs and data

- **Cancelling a running job can take up to 10 seconds**: the worker gets that long to stop
  before it is killed, and the cancel request waits for it.
- **Jobs that belong to no project are not listed** by `GET /api/v1/jobs`; administrators can
  still read them by id.
- **Deleting a project or a dataset removes its record first and its files second.** If the
  storage fails in between, files can be left behind in the bucket.
- **Only the latest export of all models is kept** per project; a new export replaces it.
  Anyone who can read the project can start an export.
- **Datasets are loaded whole into memory** for training, batch prediction and Python modules
  (there is no out-of-core processing). Measured on a 16-core Mac, a training job peaked at about
  1.9 GB of memory for a 150 MB CSV (200,000 rows × 42 columns) and 2.5 GB for a 750 MB CSV
  (1,000,000 × 42); roughly 1.5–1.7 GB of that does not grow with the data (the libraries). Plan
  for at least 4 GB of RAM, and more for wider data or larger files.
- **Cross-validation scores are slightly optimistic.** Boosting models stop early on their
  validation fold, and the ensemble's weights are chosen on the same out-of-fold predictions it
  is scored on. The leaderboard's ensemble row and the star rating inherit this; test data held
  back from training gives the honest number.
- **The engine uses about two thirds of the maximum run time** in practice (search and final
  refit leave budget unused); a more adaptive search is planned.
- **On a heavily loaded machine the time budget buys fewer boosting rounds**; CatBoost is
  affected most.
- **Training and engine messages are in English** in the Japanese UI.

## Explanations and leak warnings

- **Contributions are approximations.** Each row's contributions (on the result page, through
  the API, in batch predictions and from Fione Serving) add up to the prediction, to rounding,
  in probability for classification and in the target's units for regression, not in log-odds.
  They start from each library's own TreeSHAP (LightGBM, XGBoost, CatBoost) and from Saabas
  path contributions for ExtraTrees, and are then converted to probabilities and combined over
  the ensemble; exact Shapley values exist only for each booster on its own, before that
  conversion. With more than two classes the conversion is a numerical path integral whose
  small remainder is shared out so that the sum stays exact.
- **One output is explained per row**: with two classes the second one (the last `p_` column),
  with more the predicted class (the API takes a `class_index` for another), for regression
  the value. Batch predictions and Fione Serving have no option for every class.
- **Explanations need a dataset.** The explain job (queued after each training unless
  `FIONE_EXPLAIN_AFTER_TRAINING` is `false`) and the curves computed on request use the
  model's training data. An imported model, or one whose training data was deleted, has none:
  choose a dataset with the model's columns under **Compute the explanation** on the
  **Explain** tab. Until then the web pages show only curves already stored for it.
- **What the explain job stores**: importance from the contributions of at most 1,000 rows
  (fewer for models with many classes × columns), sampled by class, and the partial dependence
  of the 10 most important columns. Each curve takes its grid from a 10,000-row sample and
  averages over 300 of those rows (fewer for wide models). A result above 1 MiB, which only
  very wide models or very long names reach, is trimmed: the least important columns beyond
  1,000 first, then the single-row (ICE) lines, then whole curves. Nothing marks a trimmed
  result.
- **Partial dependence grids** run from the 2nd to the 98th percentile, so a long tail (for
  example Adult's capital gains above about 15,000) is not shown. Numeric grids have no point
  for missing values; category grids do. Times with a time zone are shown in UTC. Category
  levels the model never saw in training can take places on a grid, and count as unknown
  there. A curve computed on request (a column without a stored curve, or the API) takes its
  grid as well as its rows from at most 300 rows (fewer for wide models), so its points can
  differ from those of a stored curve.
- **The web process now loads models.** Before explanations, it never loaded a model file.
  Now it loads trusted models to explain on request: the reasons for the first 5 rows when a
  prediction's result page is opened, contributions of up to 100 rows, and the partial
  dependence of one column. Viewers can ask for these. Up to 2 models and 512 MiB of model
  files stay loaded.
- **Explanations asked for on the spot are computed one at a time** for the whole server.
  While one runs, up to four more wait, for 15 s at most; any others get a "busy" answer (HTTP
  503) at once, so one busy reader can delay everyone's. Models whose file is over 512 MiB
  (409), imports not vouched for (409), and models with too many rows × classes × columns
  for the request (422) are refused there and explained only by the explain job, which needs
  write access. The rows for one partial dependence curve come from the start of up to 8 parts
  of the dataset file; on a dataset with thousands of columns that read alone can take a few
  hundred MiB.
- **Explain jobs are listed with the other jobs**, but the dashboard's recent jobs leave them
  out.
- **Contribution columns in batch predictions** (**Explain each prediction** on the
  prediction form, `include_contributions` in the API): a `contrib_<column>` per model input,
  then `contrib_bias` (`contrib_bias_2` when an input is named `bias`); an input column whose
  name is taken is kept as `input_<name>`. Each row gains
  one float64 column per input plus one, so 100,000 rows of a 2,000-column model make about
  1.6 GB of output. At most 100,000 rows; the work runs on at most 4 threads, in chunks of at
  most 5,000 rows, and is much slower than a plain prediction.
- **Diagnostics** (the Metrics tab) come from the ensemble's out-of-fold predictions, so they
  are slightly optimistic, like the cross-validation scores. Above 200,000 rows they come from
  a random sample. A model has none when it was trained before they existed or imported
  without them, or when they could not be computed or took more than 256 KiB.
- **Only exact leaks are unchecked.** A column identical to the column to predict, or whose
  value determines it, is left out of the EasyML defaults (row IDs stay unchecked as IDs, as
  before). A column that only scores high stays checked, with a warning: one that predicts
  the answer on its own, one whose order or gaps follow the answer, and one with a
  near-perfect correlation (|r| ≥ 0.99), which used to be unchecked.
- **Leak scores are warnings and can be wrong both ways.** A strong legitimate column can be
  flagged, and a leak can be missed; no warning does not mean no leak. A column is flagged at a
  single-column AUC of 0.95 (R² 0.90 for regression) and 0.10 above the best column under
  that line, or at 0.99 in any case. So beside a column that already scores 0.89-0.95, only a
  score of 0.99 warns: a copy of the answer with 1% of its values wrong (0.987, measured beside
  the breast cancer dataset's columns) goes unreported. A column that is zero for every row of one class
  and for some rows of the other (an amount filled in for 80% of the positives) scores at most
  0.90 and is never flagged. Regression leaks are mostly missed below about 5,000 rows.
  Targets with more than 100 classes get no score at all, and the screens do not say so; only
  the exact checks run. Scores use at most 10,000 rows, datasets under 200 rows are not
  scored, and after 3 s the check stops and says that some columns were not scored.

## Notebooks

Notebooks are opt-in (the Compose profile `notebook`); see [Notebooks](notebook.md).

- **The launcher holds the Docker socket**, which is root-equivalent on the host. Only the
  `notebook-launcher` service has it, with all capabilities dropped and a read-only
  filesystem, and it starts containers from one fixed spec; Fione never touches the socket.
  A flaw in the launcher would be a flaw in the host's security. It answers only on a
  network that Fione alone shares, checks a shared secret, and accepts nothing but
  fixed-format values; keep notebooks off unless you need them.
- **A notebook container sees its owner's API token and keys.** The container's environment
  holds `FIONE_TOKEN` (which code in the notebook reads, by design) and the sign-in keys, and
  anyone who can use Docker on the host can read them (`docker inspect`). The token expires
  with the notebook, acts at most as an editor, and cannot manage accounts, tokens, modules,
  imports or sharing.
- **A viewer who is granted notebooks still runs code**, with a token that can only read the
  data they may read. Granting notebooks gives a user a container with 2 CPUs, 4 GiB of memory,
  512 processes and no capabilities, on an internal network with no egress.
- **The Docker host answers on the `notebooks` network.** The network is internal (no route
  out), but the host's own address on its bridge (the subnet's first address) accepts
  connections from notebook code: every host service bound to all interfaces (`0.0.0.0`),
  such as SSH, is reachable from every notebook through that address. The mitigation is a
  host firewall: `INPUT` rules that drop traffic from the `notebooks` bridge to the host
  (`DOCKER-USER` sees only forwarded traffic, so it covers other destinations, not the host
  itself), or binding host services to the addresses they serve. Fione does not ship such
  rules; whether to is an open decision for the maintainer. The end-to-end tests record what
  answers on ports 22 and 80 there, without asserting it.
- **The notebooks of different users share one network.** Another user's container is
  reachable at TCP level on the internal network `notebooks`; each JupyterLab refuses everyone
  but its owner.
- **Notebook users share one browser origin.** Every user's JupyterLab is served from the
  gateway's origin (`/user/<id>/`), and trusted notebook output (HTML and JavaScript that a
  user's own cells produced) runs there unsandboxed: it is content a user can write, on the
  origin all users share. Script there could reach the JupyterLab of another user whose
  browser is signed in to it. The way to that is a sign-in of the victim's browser into the
  attacker's notebook; JupyterLab accepts a sign-in only from a same-site navigation whose
  `Referer` is Fione's origin, which closes it from other sites and from other pages on the
  same site. Until per-user subdomains are adopted (`u<id>.nb.example.com`, which needs
  wildcard DNS and TLS; an open decision for the maintainer), treat notebook users as trusting
  each other.
- **The site is the trust boundary.** Every origin on the gateway's registrable domain, and
  every port on the same local host name, is same-site with it, and browsers send cookies to
  the gateway from those pages' requests. Give the gateway a registrable domain used for
  nothing but Fione (see [The same-site rule](notebook.md#the-same-site-rule)).
- **Code in a notebook runs as the same operating-system user as the Jupyter server of that
  container.** A user can therefore in principle inspect that server's process (`ptrace`,
  `/proc`), and with it the container's launch key and cookie secret. Reading the key needs
  less: the owner can read their container's own launch key from the server's process
  environment and mint launch tokens (with any role claim) for their own container. Both stay
  inside the user's own container and identity: what they can do to Fione is limited by their
  token, and other containers have other keys. A seccomp profile that denies `ptrace` and
  `process_vm_writev` would close the first; that is an open decision too.
- **Notebook trust signatures are kept in memory** (the data directory is read-only) and are
  lost when the container restarts: outputs of notebooks saved earlier show as untrusted until
  the cells are run again.
- **JupyterLab's settings and layout are not saved.** The gateway refuses writes to its
  settings and workspaces.
- **Notebooks end.** A kernel idle for 30 minutes is stopped when no JupyterLab tab has it
  open; a notebook with no kernel and no activity for 1 hour shuts down; and every notebook
  ends after
  `FIONE_NOTEBOOK_MAX_LIFETIME_SECS` (12 hours by default), together with its token. Running
  kernels are lost whenever the container goes: on stop, on shutdown and when the launcher
  restarts or `docker compose down` stops it. The files in the user's volume stay.
- **An open JupyterLab tab keeps its notebook running.** Idle culling skips kernels that a tab
  has open, and a notebook with a running kernel does not shut down, so a forgotten tab keeps
  the container until its lifetime ends and holds one of the `FIONE_NOTEBOOK_MAX_RUNNING`
  places.
- **At most `FIONE_NOTEBOOK_MAX_RUNNING` notebooks run at once** (4 by default), whatever the
  host can carry. Each may use 2 CPUs and 4 GiB, so four use up to 8 CPUs and 16 GiB beside
  Fione's own jobs.
- **Notebook disk use has no limit.** Neither the users' volumes nor the containers' own files
  have a quota: one user can fill the Docker host's disk, which Fione's database and storage
  volumes share.
- **There is no egress.** Code in a notebook cannot install packages or fetch data; the
  libraries are the image's (JupyterLab, pandas, pyarrow, scikit-learn, matplotlib, httpx and
  `fione-sdk`).
- **The gateway's relay refuses raw paths with a `.` or `..` segment.** For a column named
  exactly `.` or `..`, a notebook cannot fetch the column's profile (`column_profile` puts the
  name in the path); reading the whole dataset still works.
- **The gateway also sits on a network with a route out**, because its port is published, so
  Docker's DNS may pass a lookup of an unknown `nb-<digits>` name on to the host's resolvers.
  Docker's DNS answers for the aliases of running notebooks; the gateway re-asks every 10 s, so
  a notebook that was replaced may still be reachable at its old address for up to 10 s.
- **JupyterLab's `_xsrf` cookie is not marked `Secure`** behind HTTPS. It guards form posts and
  is not a credential; the sign-in cookie is `Secure` when `FIONE_PUBLIC_URL` is `https`.
- **Deleting a user removes their notebook and its files** (the volume). If the launcher cannot
  be reached at that moment, Fione deletes the user anyway, and the removal is pending (see the
  next item); no notebook starts for that user id (Fione reuses ids) until it is done. The
  volumes also outlive `docker compose down -v`, and a reset install starts its user ids
  again, so remove them by label before creating users on one, as
  [Notebooks](notebook.md#files-and-persistence) shows.
- **Stopping a notebook can be pending.** Revoking the permission, a new password, taking the
  administrator role away and deleting the user end the notebook's token at once, but the
  container is removed by the launcher. If the launcher cannot be reached, the change is made
  anyway, the **Users** page (or the API's `notebook_stop_pending` notice) says so, and Fione
  retries every minute and before every notebook start, stop and status check. Until a retry succeeds, a browser
  already signed in to that JupyterLab keeps using it (the sign-in cookie lasts as long as
  the container). Pending stops are kept in Fione's database, so a restart keeps retrying.
- **The launcher and Fione keep notebook state in the process**: the per-user start and stop
  locks of Fione, and the launcher's start lock, are in memory, so run one of each (see
  *One process only* below).
- **Stopping a notebook while JupyterLab is open** can leave errors in the browser's console
  (502, "Failed to fetch"); and the first Shift+Enter in a fresh notebook is sometimes ignored
  (stock JupyterLab does it too).
- **Untested:** Firefox and Safari for the notebook page (the tests use Chromium), rootless
  Docker and Podman as the container runtime.
- **The notebook image is large**: about 950 MB (947 MB measured on arm64), mostly Python,
  JupyterLab and the data libraries.

## Deployment

- **One process only.** Run the `fione` service with one worker and do not scale it (see
  [Configuration](configuration.md#one-worker-process)); the same goes for the
  `notebook-launcher` service.
- **The images are large**: about 1.65 GB (`fione`) and 1.7 GB (`fione-serving`), mostly the
  machine-learning libraries.
- **No images are published yet.** You build them from the repository. On a version tag the
  release workflow publishes the `fione`, `fione-serving`, `fione-notebook` and
  `fione-notebook-launcher` images, for amd64 only, and it does not wait for the tests of the
  tagged commit: tag only commits whose CI has passed.
- **On Linux, XGBoost brings NVIDIA's NCCL library** (`nvidia-nccl-cu13`, about 350 MB of the
  `fione` and `fione-serving` images), although Fione trains on CPUs only. Its package metadata
  declares the licence `LicenseRef-NVIDIA-Proprietary`, while the licence file inside the
  wheel is a BSD-3-Clause-style text; the licence check reports it for review rather than as
  allowed. Review it before redistributing the images. The CPU-only `xgboost-cpu` package
  (Apache-2.0, no NCCL) has no macOS wheels, so it is not used.
- **Base images are pinned by tag, not by digest**, so a rebuild can pick up a patched base
  image.
- **Models are tied to the image tag.** Fione Serving loads only models trained by an image of
  the same tag, and a model trained by an older version is not guaranteed to load in a newer
  one.
- **Starlette is pinned below 1.10**: the upload handling uses Starlette internals that must be
  checked before allowing a newer version.

## Fione-kun and MCP

- **Answers can be wrong.** The default model is small. Check results you rely on; a training
  it suggests runs only after a person confirms it.
- **Names and statistics reach the language model server.** Dataset and column names and
  statistics are sent with each question; cell values only if an administrator allows
  example values for that server. With a server outside this machine, every chat user is warned.
- **Text from the data can steer what Fione-kun says, not what it does.** Fione-kun can only
  read and propose, and a proposal starts nothing until a person confirms it.
- **Calls to a real model's tools are checked only by an opt-in test.** The tests of the
  default suite use a fake server (`tests/llm` runs against a real one, by hand).
- **MCP uses a full API token** (the same rights as the REST API), runs at most two tool calls
  at once and has no other rate limit. It is off by default.
- **An answer that is running when Fione restarts is lost** (it ends as interrupted).
- **In Docker on macOS, Ollama runs on the CPU only**, so the default is the Ollama app on the
  host, which Compose reaches as `host.docker.internal`.
- **The Ollama image is about 3.8 GB and the default model about 8 GB.**
- **Conversations are stored unencrypted** in the database, and not even administrators can
  see them in Fione.
- **Abandoned requests to a misbehaving model server can hold connections** of the shared
  pool (about 100) until the server's own timeout; see [Configuration](configuration.md).
- **A server name without dots counts as local**, but a resolver's search domain can make it
  reach a remote host; see `FIONE_LLM_BASE_URL` in [Configuration](configuration.md).
- **The context warning on the System page appears only while the model is loaded**, because
  Ollama reports the context length of a loaded model only.

## Browser

- **Dark mode needs Chrome or Edge 123+, Firefox 120+ or Safari 17.5+** (CSS `light-dark()`);
  older browsers get the light theme only. There is no "follow the system" setting once the
  theme was switched by hand (clear the site data to reset it).
- **Japanese line breaking by phrase** (`word-break: auto-phrase`) needs Chrome or Edge 119+;
  other browsers wrap normally.
- **Sign-in needs JavaScript.**
- **The simple / detailed view is remembered per browser** (a cookie), not per user.

## 日本語の要約

- サーバー側でセッションを無効にできません（ログアウトはそのブラウザの Cookie を消すだけ。パスワード変更で全セッションが終了）。
- 管理者がパスワードを再設定しても、そのユーザーの API トークンは残ります。管理者用のトークン管理画面はありません。自分で作ったトークンは期限切れになりません（ノートブック用のトークンはノートブックと一緒に期限切れになり、編集者の権限までで、アカウント・トークン・モジュール・インポート・共有は操作できません）。
- アップロードした Python モジュールはサンドボックスなしで、サーバーと同じ権限で動きます（アップロードは管理者のみ）。待機中のジョブは、実行時点のモジュールのソースで動きます。
- 管理者以外に見せるエラーメッセージからファイルのパスは消えますが、URL やホスト名は残ります。
- CSV のダウンロードは数式インジェクション対策をしていません。
- 管理者ができるまで、セットアップトークンがログに残ります。S3 の認証情報は `docker inspect` で見えます。
- 実行中のジョブのキャンセルには最大 10 秒かかります。プロジェクトに属さないジョブは `GET /api/v1/jobs` に出ません。削除中にストレージが失敗すると、ファイルが残ることがあります。
- 全モデルのエクスポートは、プロジェクトごとに最新の 1 つだけ残ります。
- エンジンは実際には最大実行時間の約 3 分の 2 を使います。学習やエンジンのメッセージは日本語画面でも英語です。
- 寄与度は近似です。各行の寄与度は予測値（分類では確率、回帰では目的変数の単位。log-odds ではありません）に丸め誤差の範囲で一致しますが、各ライブラリの TreeSHAP（ExtraTrees は Saabas）を確率に変換してアンサンブルで合成したもので、厳密な Shapley 値ではありません。説明するのは 1 行につき 1 つの出力です（2 クラスでは 2 番目のクラス、それ以上では予測したクラス、回帰では値）。
- 説明には学習データが必要です。インポートしたモデルや学習データを削除したモデルは、「説明」タブの「説明を計算」で、列のそろったデータセットを選んでください。説明ジョブが保存するのは、最大 1,000 行の寄与度による重要度と、上位 10 列の部分依存です。曲線のグリッドは 1 万行のサンプルから作り、そのうち 300 行（列の多いモデルではもっと少なく）で平均します。1 MiB を超える結果は、目印なしで削られます。
- 部分依存のグリッドは 2〜98 パーセンタイルまでで、数値の列には欠損値の点がありません。時刻は UTC です。学習で見なかったカテゴリもグリッドに入ることがあります。その場で計算する曲線はグリッドも平均も最大 300 行から作るので、保存した曲線と点が少し違うことがあります。
- Web プロセスがモデルを読み込むようになりました（閲覧者の操作でも）。結果画面での先頭 5 行の理由、最大 100 行の寄与度、1 列の部分依存を、サーバー全体で 1 件ずつ計算します。待てるのは 4 件まで、最大 15 秒で、それ以外はすぐに「混雑」（HTTP 503）になります。読み込んだままにするのは 2 モデル・512 MiB までです。ファイルが 512 MiB を超えるモデル、信頼を確認していないインポート、行 × クラス × 列が多すぎるモデルはそこでは断り、書き込み権限が必要な説明ジョブでだけ説明します。列が数千あるデータセットでは、部分依存 1 回の読み込みだけで数百 MiB 使うことがあります。説明ジョブはジョブ一覧に出ますが、ダッシュボードの最近のジョブには出ません。
- バッチ予測で「各予測の内訳を含める」を選ぶと付く列は `contrib_<列>` と `contrib_bias`（入力に `bias` という列があると `contrib_bias_2`）で、名前がぶつかる入力列は `input_<名前>` になります。1 行あたり入力の列数 + 1 個の float64 の列が増え（2,000 列のモデルで 10 万行なら約 1.6 GB）、最大 10 万行、4 スレッドまでで計算するので、通常の予測よりかなり遅くなります。
- 診断（指標タブ）は学習時の out-of-fold 予測から作るため、CV のスコアと同じくやや楽観的です。20 万行を超えるとランダムサンプルから作ります。
- モデルの診断には学習データの値が含まれます（クラスのラベルと、回帰では学習行から抜き出した最大 2,000 件の実際の値とその予測値）。プロジェクトを読めるすべての人に見え、モデルのエクスポートにも入り、学習データを削除しても残ります。保存した説明も、カテゴリやクラスのラベルをデータセット削除後も保持します（エクスポートはされません）。モデルファイルとサービング用ファイルには診断は入りません。
- 診断を持つエクスポートは、診断の機能より前のインストールでは読み込めません（どちらもバージョン 20.0.0 で区別できません）。インポートは、有限でない数や float の範囲を超える整数（診断の中も含め、どこにあっても）、未知の項目や深すぎる入れ子を持つ診断を拒否するようになりました。
- リークとして既定でチェックを外すのは完全なもの（予測する列と同じ列、値で答えが決まる列）だけです（行の ID の列はこれまでどおり ID としてチェックを外します）。スコアによる疑い（単独で答えをよく当てる列、並び順や欠損が答えに沿う列、相関 |r| ≥ 0.99 の列。相関の列は以前はチェックを外していました）は注意を出すだけで、チェックされたままです。
- リークのスコアは注意であり、どちらの向きにも間違えます。強い正当な列が疑われることも、リークを見逃すこともあります。すでに 0.89〜0.95 の列がある場合は 0.99 以上だけが注意になり、値の 1% が違う答えのコピー（0.987）は報告されません。一方のクラスで常に 0 の列（もう一方の 80% だけ値がある金額など）は最大 0.90 で、報告されません。回帰のリークは約 5,000 行未満ではほとんど見逃します。101 クラス以上の目的変数にはスコアがなく、画面にもそう表示されません。200 行未満のデータセットは採点せず、3 秒で打ち切ると、採点しなかった列があることを表示します。
- 負荷の高いマシンでは、同じ時間予算で学習できるブースティングの回数が減ります。いちばん影響を受けるのは CatBoost です。
- API トークンに有効期限はなく、最後に使われた日時も記録しません。不要なトークンは無効にしてください。
- Fione Serving には認証も、予測のリクエスト数・同時実行数の制限もありません。寄与度を求めるリクエストだけは同時に 2 件まで（それ以上は 503）ですが、計算中はモデルを占有するので、通常の予測はその間待たされます。最大のリクエストでは約 100 MiB のメモリを使います。画面に出る `-p 8081:8080` はすべてのネットワークインターフェースで公開するので、このマシンだけで使うなら `-p 127.0.0.1:8081:8080` にしてください。
- 学習・バッチ予測・Python モジュールはデータセット全体をメモリに読み込みます。16 コアの Mac で、150 MB の CSV（20 万行 × 42 列）で最大約 1.9 GB、750 MB の CSV（100 万行 × 42 列）で約 2.5 GB でした（うち約 1.5〜1.7 GB はデータの大きさによらない分）。メモリは 4 GB 以上を目安にしてください。
- CV のスコアはやや楽観的です（早期終了とアンサンブルの重みが同じ fold の予測で決まるため）。正直な数値は、学習に使わないテストデータで確かめてください。
- Linux では XGBoost が NVIDIA の NCCL ライブラリ（`nvidia-nccl-cu13`、イメージ内で約 350 MB）を取り込みます。パッケージのメタデータはライセンスを `LicenseRef-NVIDIA-Proprietary` としており、ホイール内のライセンス文は BSD-3-Clause 型です。イメージを再配布する前に確認してください（CPU 専用の `xgboost-cpu` は macOS 用のホイールがないため使っていません）。
- 1 プロセス・1 ワーカーで動かしてください。イメージは約 1.65 GB / 1.7 GB で、まだ公開していません（リリースは amd64 のみ、タグは CI が通ったコミットにだけ付けてください）。ベースイメージはタグ固定で、ダイジェスト固定ではありません。
- モデルはイメージのタグに結び付いています。古い版のモデルが新しい版で読み込める保証はありません。
- ノートブックは任意の機能です（Compose のプロファイル `notebook`）。ランチャーは Docker ソケットを持ち、これはホストの root と同等です。ノートブックのコンテナには、所有者の API トークン（`FIONE_TOKEN`）と鍵が環境変数に入り、ホストで Docker を使える人には `docker inspect` で見えます。ノートブックを許可された閲覧者もコードを実行できます（トークンは読み取り専用）。コンテナの上限は CPU 2、メモリ 4 GiB、プロセス 512、ケーパビリティなし、外部通信なしで、同時に動くノートブックは既定で 4 つまで（`FIONE_NOTEBOOK_MAX_RUNNING`）です。
- 他のユーザーのコンテナとは、内部ネットワーク上で TCP としては到達できます（各 JupyterLab は所有者以外を拒否します）。`notebooks` は外へ出られない内部ネットワークですが、そのブリッジ上のホスト自身のアドレス（サブネットの最初のアドレス）には接続できるため、すべてのアドレス（`0.0.0.0`）で待ち受けるホストのサービス（SSH など）にはノートブックから届きます。対策はホストのファイアウォールです（`notebooks` のブリッジからホストへの通信を落とす `INPUT` のルール。`DOCKER-USER` は転送される通信しか見ないため、ホスト自身は守れません）。または、ホストのサービスを必要なアドレスだけで待ち受けるようにします。Fione はそのルールを同梱していません（同梱するかは未決事項）。全ユーザーの JupyterLab は 1 つのオリジンを共有し、信頼済みのノートブックの出力（ユーザーが書ける内容）はそこでサンドボックスなしに動きます。ログインは、同一サイトからで `Referer` が Fione のオリジンのものだけを受け付けるため、他のサイトや同じサイトの他のページから被害者のブラウザを攻撃者のノートブックにログインさせることはできません。ユーザーごとのサブドメインを採用するまで（未決事項）、ノートブックのユーザー同士は信頼し合うものとして扱ってください。同じ登録可能ドメインのすべてのオリジン（ローカルでは同じホスト名のすべてのポート）がゲートウェイと同一サイトになるため、ゲートウェイには Fione 専用の登録可能ドメインを使ってください。ノートブックのコードは、コンテナ内の Jupyter サーバーと同じ OS ユーザーで動くため、ユーザーは自分のコンテナのサーバーのプロセスを調べられます（対策は seccomp で `ptrace` と `process_vm_writev` を拒否すること。これも未決事項）。所有者は自分のコンテナの起動用の鍵をサーバーのプロセスの環境変数から読んで、自分のコンテナ用の起動トークンを作れます（他のコンテナには影響しません）。
- ノートブックの信頼の署名はメモリにだけあり、再起動で失われます。JupyterLab の設定とレイアウトは保存されません。実行中のカーネルは、停止時、ランチャーの再起動時、`docker compose down` で失われます。JupyterLab のタブで開かれていない、30 分使われないカーネルは停止し（開いたままのタブはノートブックを寿命まで動かし続け、同時実行の枠を 1 つ使います）、実行中のカーネルがなく 1 時間操作がないノートブックは終了し、`FIONE_NOTEBOOK_MAX_LIFETIME_SECS`（既定 12 時間）でも必ず終了します。
- ゲートウェイの中継は、`.` や `..` の区間を含む生のパスを拒否するため、名前がちょうど `.` または `..` の列は、ノートブックから列ごとの概要（`column_profile`）を取得できません（データセット全体の読み込みはできます）。ゲートウェイは外へ出られるネットワークにも属するため、未知の `nb-<数字>` の名前の問い合わせがホストの DNS に渡ることがあり、入れ替えたノートブックに古いアドレスで最大 10 秒届くことがあります。HTTPS でも JupyterLab の `_xsrf` Cookie には `Secure` が付きません（認証情報ではありません）。
- ユーザーを削除するとノートブックとそのファイルも削除されます。`docker compose down -v` でもボリュームは残り、初期化したインストールではユーザー ID が最初からになるため、その場合もユーザーを作る前にラベルを指定して削除してください。そのときランチャーに届かないと削除は保留になり、成功するまでその ID のノートブックは起動しません。Fione とランチャーは 1 プロセスで動かしてください。
- 権限の取り消し、新しいパスワード、管理者のロールを外すこと、ユーザーの削除では、ノートブックのトークンはすぐに無効になりますが、コンテナを削除するのはランチャーです。ランチャーに届かないと停止は保留になり、「ユーザー」画面（API では `notebook_stop_pending`）に表示され、Fione が 1 分ごとと、ノートブックの起動・停止・状態確認のたびに再試行します。成功するまで、すでにその JupyterLab にログインしているブラウザは使い続けられます。保留中の停止はデータベースに残るため、再起動しても再試行が続きます。
- JupyterLab を開いたまま停止すると、ブラウザのコンソールにエラーが出ることがあります。新しいノートブックの最初の Shift+Enter が無視されることがあります（標準の JupyterLab でも起こります）。Firefox と Safari、rootless Docker、Podman は検証していません。ノートブックのイメージは約 950 MB（arm64 で 947 MB を測定）です。ノートブックのボリュームとコンテナのファイルには容量の上限がなく、1 人のユーザーがホストのディスクを使い切ることがあります。
- ダークモードは Chrome / Edge 123 以降、Firefox 120 以降、Safari 17.5 以降が必要です。ログインには JavaScript が必要です。簡易・詳細の表示はブラウザごとに記憶されます。
- Fione 君と MCP：答えは間違うことがあります（モデルは小さい）。学習の提案は人が確認して初めて動きます。名前と統計は言語モデルのサーバーに届きます（セルの値は管理者が許したときだけ）。データ内の文章は Fione 君の発言を左右できても、動作は左右できません。実モデルでのツール呼び出しは opt-in のテストでしか確かめていません。MCP は full の API トークンを使い、同時 2 呼び出しまでで、他のレート制限はなく、既定はオフです。回答中の再起動でその回答は失われます。macOS の Docker では Ollama は CPU だけで動くため、既定はホストの Ollama アプリです。Ollama のイメージは約 3.8 GB、モデルは約 8 GB です。会話は暗号化せずに保存され、管理者にも見えません。異常なモデルサーバーへの放棄された要求は、サーバーのタイムアウトまで共有の接続プール（約 100）を占めることがあります。ドットのないサーバー名は「ローカル」とみなされますが、リゾルバーの検索ドメインでリモートに届くことがあります。システムページのコンテキスト警告はモデルがロードされている間だけ出ます。

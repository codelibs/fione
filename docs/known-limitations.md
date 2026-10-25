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
- **API tokens never expire**, and Fione does not record when one was last used. Revoke tokens
  you no longer need on the Account page.
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
  of the 10 most important columns over a 10,000-row sample. A result above 1 MiB, which only
  very wide models or very long names reach, is trimmed: the least important columns beyond
  1,000 first, then the single-row (ICE) lines, then whole curves. Nothing marks a trimmed
  result.
- **Partial dependence grids** run from the 2nd to the 98th percentile, so a long tail (for
  example Adult's capital gains above about 15,000) is not shown. Numeric grids have no point
  for missing values; category grids do. Times with a time zone are shown in UTC. Category
  levels the model never saw in training can take places on a grid, and count as unknown
  there. A curve computed on request (a column without a stored curve, or the API) averages
  over at most 300 rows (fewer for wide models), so it can differ from the stored curves,
  which use 10,000.
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

## Deployment

- **One process only.** Run the `fione` service with one worker and do not scale it (see
  [Configuration](configuration.md#one-worker-process)).
- **The images are large**: about 1.65 GB (`fione`) and 1.7 GB (`fione-serving`), mostly the
  machine-learning libraries.
- **No images are published yet.** You build them from the repository. The release workflow
  publishes amd64 images only, and it does not wait for the tests of the tagged commit: tag
  only commits whose CI has passed.
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
- 管理者がパスワードを再設定しても、そのユーザーの API トークンは残ります。管理者用のトークン管理画面はありません。
- アップロードした Python モジュールはサンドボックスなしで、サーバーと同じ権限で動きます（アップロードは管理者のみ）。待機中のジョブは、実行時点のモジュールのソースで動きます。
- 管理者以外に見せるエラーメッセージからファイルのパスは消えますが、URL やホスト名は残ります。
- CSV のダウンロードは数式インジェクション対策をしていません。
- 管理者ができるまで、セットアップトークンがログに残ります。S3 の認証情報は `docker inspect` で見えます。
- 実行中のジョブのキャンセルには最大 10 秒かかります。プロジェクトに属さないジョブは `GET /api/v1/jobs` に出ません。削除中にストレージが失敗すると、ファイルが残ることがあります。
- 全モデルのエクスポートは、プロジェクトごとに最新の 1 つだけ残ります。
- エンジンは実際には最大実行時間の約 3 分の 2 を使います。学習やエンジンのメッセージは日本語画面でも英語です。
- 寄与度は近似です。各行の寄与度は予測値（分類では確率、回帰では目的変数の単位。log-odds ではありません）に丸め誤差の範囲で一致しますが、各ライブラリの TreeSHAP（ExtraTrees は Saabas）を確率に変換してアンサンブルで合成したもので、厳密な Shapley 値ではありません。説明するのは 1 行につき 1 つの出力です（2 クラスでは 2 番目のクラス、それ以上では予測したクラス、回帰では値）。
- 説明には学習データが必要です。インポートしたモデルや学習データを削除したモデルは、「説明」タブの「説明を計算」で、列のそろったデータセットを選んでください。説明ジョブが保存するのは、最大 1,000 行の寄与度による重要度と、上位 10 列の部分依存（1 万行のサンプル）です。1 MiB を超える結果は、目印なしで削られます。
- 部分依存のグリッドは 2〜98 パーセンタイルまでで、数値の列には欠損値の点がありません。時刻は UTC です。学習で見なかったカテゴリもグリッドに入ることがあります。その場で計算する曲線は最大 300 行の平均なので、保存した曲線（1 万行）と少し違うことがあります。
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
- ダークモードは Chrome / Edge 123 以降、Firefox 120 以降、Safari 17.5 以降が必要です。ログインには JavaScript が必要です。簡易・詳細の表示はブラウザごとに記憶されます。

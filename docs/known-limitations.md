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
- **Fione Serving has no authentication** and no rate or concurrency limit (only the request
  size limits). The command the UI shows, `docker run --rm -p 8081:8080 …`, publishes it on every
  network interface of the host; use `-p 127.0.0.1:8081:8080` to keep it on that machine, and a
  reverse proxy with authentication to serve others.
- **Imported models** that were not made by this installation load only if an administrator
  ticks the trust option on import; the model is then marked "Imported, unverified". Loading
  a model file runs code, so trust only files you know.

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
- **Explanations asked for on the spot are computed one at a time** in the web process
  (contributions of up to 100 rows, partial dependence of one column). While one runs, up to
  four more wait, for 15 s at most; any others get a "busy" answer (HTTP 503) at once. Models
  whose file is over 512 MiB, imports not vouched for, and models with too many classes ×
  columns for the rows asked are refused there and explained only by the explain job, which
  needs write access.

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
- その場で求める説明（最大 100 行の寄与度、1 列の部分依存）は Web プロセスで 1 件ずつ計算します。待てるのは 4 件まで、最大 15 秒で、それ以外はすぐに「混雑」（HTTP 503）になります。ファイルが 512 MiB を超えるモデル、信頼を確認していないインポート、求めた行数に対してクラス × 列が多すぎるモデルはそこでは断り、書き込み権限が必要な説明ジョブでだけ説明します。
- 負荷の高いマシンでは、同じ時間予算で学習できるブースティングの回数が減ります。いちばん影響を受けるのは CatBoost です。
- API トークンに有効期限はなく、最後に使われた日時も記録しません。不要なトークンは無効にしてください。
- Fione Serving には認証も、リクエスト数・同時実行数の制限もありません。画面に出る `-p 8081:8080` はすべてのネットワークインターフェースで公開するので、このマシンだけで使うなら `-p 127.0.0.1:8081:8080` にしてください。
- 学習・バッチ予測・Python モジュールはデータセット全体をメモリに読み込みます。16 コアの Mac で、150 MB の CSV（20 万行 × 42 列）で最大約 1.9 GB、750 MB の CSV（100 万行 × 42 列）で約 2.5 GB でした（うち約 1.5〜1.7 GB はデータの大きさによらない分）。メモリは 4 GB 以上を目安にしてください。
- CV のスコアはやや楽観的です（早期終了とアンサンブルの重みが同じ fold の予測で決まるため）。正直な数値は、学習に使わないテストデータで確かめてください。
- Linux では XGBoost が NVIDIA の NCCL ライブラリ（`nvidia-nccl-cu13`、イメージ内で約 350 MB）を取り込みます。パッケージのメタデータはライセンスを `LicenseRef-NVIDIA-Proprietary` としており、ホイール内のライセンス文は BSD-3-Clause 型です。イメージを再配布する前に確認してください（CPU 専用の `xgboost-cpu` は macOS 用のホイールがないため使っていません）。
- 1 プロセス・1 ワーカーで動かしてください。イメージは約 1.65 GB / 1.7 GB で、まだ公開していません（リリースは amd64 のみ、タグは CI が通ったコミットにだけ付けてください）。ベースイメージはタグ固定で、ダイジェスト固定ではありません。
- モデルはイメージのタグに結び付いています。古い版のモデルが新しい版で読み込める保証はありません。
- ダークモードは Chrome / Edge 123 以降、Firefox 120 以降、Safari 17.5 以降が必要です。ログインには JavaScript が必要です。簡易・詳細の表示はブラウザごとに記憶されます。

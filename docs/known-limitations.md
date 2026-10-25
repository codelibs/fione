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
- **The engine uses about two thirds of the maximum run time** in practice (search and final
  refit leave budget unused); a more adaptive search is planned.
- **Training and engine messages are in English** in the Japanese UI.

## Deployment

- **One process only.** Run the `fione` service with one worker and do not scale it (see
  [Configuration](configuration.md#one-worker-process)).
- **The images are large**: about 1.65 GB (`fione`) and 1.7 GB (`fione-serving`), mostly the
  machine-learning libraries.
- **No images are published yet.** You build them from the repository. The release workflow
  publishes amd64 images only, and it does not wait for the tests of the tagged commit: tag
  only commits whose CI has passed.
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
- 1 プロセス・1 ワーカーで動かしてください。イメージは約 1.65 GB / 1.7 GB で、まだ公開していません（リリースは amd64 のみ、タグは CI が通ったコミットにだけ付けてください）。ベースイメージはタグ固定で、ダイジェスト固定ではありません。
- モデルはイメージのタグに結び付いています。古い版のモデルが新しい版で読み込める保証はありません。
- ダークモードは Chrome / Edge 123 以降、Firefox 120 以降、Safari 17.5 以降が必要です。ログインには JavaScript が必要です。簡易・詳細の表示はブラウザごとに記憶されます。

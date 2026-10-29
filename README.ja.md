# Fione

Fione はオープンソースの AutoML サーバーです。ブラウザで CSV をアップロードするだけで、モデルを作り、予測し、そのモデルを予測 API として動かせます。`docker compose up` 1 回で起動します。
English: [README.md](README.md)

これは Python で書き直した Fione v2 です。Fess・H2O・MinIO にはもう依存しません。

## 機能

- **EasyML ウィザード**（機械学習が初めての人向け）：アップロード → データ分析（予測する列、入力する列、予測の種類、最大実行時間）→ 実行 → 星 1〜5 の評価と Fione 君のひと言が付いた予測結果サマリー → 予測結果の CSV と、先頭の行の予測の理由。
- **AutoML 画面**（詳細表示、専門家向け）：列ごとの統計とグラフ、相関、リークの注意、学習の全設定、ジョブ一覧、リーダーボード、変数重要度、スコア履歴、CV 指標、モデルのエクスポート・インポート。
- **モデルの説明**：交差検証の予測による診断（混同行列、クラスごとの指標、ROC 曲線と適合率-再現率曲線、キャリブレーション、残差）、各列の寄与度による重要度、部分依存の曲線、そして予測ごとの寄与度（画面、API、バッチ予測、Fione Serving）。答えを怪しいほどよく当てる列は、リークの可能性として注意を出します。
- **独自の AutoML エンジン**：LightGBM・XGBoost・CatBoost・ExtraTrees を Optuna で調整してアンサンブルし、指定した実行時間内に収めます。
- **Fione Serving**：学習したモデルを予測 API（`/invocations`、`/model`、`/ping`）として動かします。イメージは共通で、配るのはモデルのファイルだけです。
- **ユーザーと共有**：管理者・編集者・閲覧者の 3 つのロールと、ユーザーごとのプロジェクト共有。スクリプト用の API トークンと REST API（`/api/v1`）。
- **Python モジュール**によるデータ操作（組み込みのフレーム操作、k-means、低ランク分解。管理者は独自のモジュールもアップロードできます）。
- **ノートブック**（任意）：Fione の画面の中で、ユーザーごとのコンテナの JupyterLab を開けます。Python クライアント `fione-sdk` も付属します。
- **ストレージ**は SeaweedFS などの S3 互換サービス、メタデータは SQLite。
- 日本語と英語、ライト・ダークテーマ、スマートフォン表示に対応。

## クイックスタート

```sh
git clone https://github.com/codelibs/fione.git && cd fione
printf 'FIONE_S3_ACCESS_KEY=%s\nFIONE_S3_SECRET_KEY=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 32)" > docker/.env
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
docker compose -f docker/compose.yaml --env-file docker/.env logs fione | grep "Setup token"
# http://127.0.0.1:8080/ を開き、このトークンで管理者を作成します
```

サンプルデータを使った手順は[クイックスタート](docs/quickstart.ja.md)を参照してください。

## ノートブック

Fione の画面の中で、あなた専用のコンテナの JupyterLab を、二度目のログインなしで開けます。任意の機能（Compose のプロファイル `notebook`）で、`docker/.env` にアドレスを 2 つとシークレットを足します。手順は[ノートブック](docs/notebook.ja.md)を参照してください。ノートブックでも、スクリプトでも、手元の Jupyter でも、`fione-sdk`（`sdk/`、`pip install ./sdk`）と API トークンで Fione を操作できます。データセット、データの概要、AutoML の学習、リーダーボード、予測、Python モジュールを、pandas のデータフレームで扱えます。詳しくは [sdk/README.md](sdk/README.md)（英語）を参照してください。

## ドキュメント

- [クイックスタート](docs/quickstart.ja.md)（[English](docs/quickstart.md)）
- [ノートブック](docs/notebook.ja.md)（[English](docs/notebook.md)）：JupyterLab と `fione-sdk`
- [設定](docs/configuration.md)（英語）：すべての設定項目、リバースプロキシ、秘密鍵のバックアップ
- [Fione Serving](docs/serving.md)（英語）：モデルを予測 API として動かす
- [v1 から v2 への移行](docs/migrating-from-v1.ja.md)（[English](docs/migrating-from-v1.md)）
- [既知の制限](docs/known-limitations.md)（英語、末尾に日本語の要約）

## 現状

この版は中核機能（データ、分析、AutoML、モデルとその説明、予測、サービング、ジョブ、ユーザーと共有）と、任意のノートブック（JupyterLab と Python SDK）を備えています。**この版には含まれず、予定しているもの**：LLM アシスタント（Ollama。Mac では既定で `gemma4:12b-mlx`）、MCP サーバー、ONNX 出力。イメージはまだ公開していないため、リポジトリからビルドしてください（バージョンタグを付けると、`fione`、`fione-serving`、`fione-notebook`、`fione-notebook-launcher` のイメージが公開されます）。

Java 版の v1（Fess プラグイン）は、このリポジトリの v2 マージ前の履歴に残っています。

**バージョン:** このリリースは 20.0.0 です。Fione 13〜15 は Fess のバージョン番号に合わせていました。v2 は Fess に依存しないため、番号は独立し、20 から始まります。

## 開発

[uv](https://docs.astral.sh/uv/) と Python 3.12 が必要です。

```sh
uv sync                                   # 依存関係（開発用ツールを含む）
uv run pytest -q                          # 単体・API・Web・契約テスト
uv run pytest tests/e2e -m e2e            # Compose 環境に対するブラウザテスト（Docker が必要）
uv run pytest -m timing                   # 時間予算と予測速度の確認（実時間に依存）
uv run pytest -m acceptance               # エンジンの精度・サイズ・速度の受け入れテスト（データを取得）
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_licenses.py   # 依存ライブラリのライセンス検査
scripts/docker-smoke.sh                   # Docker 環境のビルドと確認
```

E2E テストには、最初に一度 Playwright 用の Chromium が必要です：`uv run playwright install chromium`

## ライセンス

Fione のライセンスは [Apache License 2.0](LICENSE) です。

依存ライブラリは Apache-2.0、MIT、BSD、ISC、PSF、0BSD のいずれかに限ります。GPL・LGPL・AGPL・非商用ライセンスは使わず、それ以外は個別に判断します。`scripts/check_licenses.py` がインストール済みのパッケージを検査し、禁止されたライセンスがあると失敗します。

Web 画面は 2 つの JavaScript ライブラリをアプリケーション自身から配信しています（CDN は使いません。[VENDOR.md](src/fione/web/static/vendor/VENDOR.md)）。

| ライブラリ | バージョン | ライセンス |
|---|---|---|
| htmx | 2.0.11 | 0BSD |
| Apache ECharts（ZRender と d3 の一部を含む） | 6.1.0 | Apache-2.0（ZRender と d3 は BSD-3-Clause） |

Compose 環境では SeaweedFS（Apache-2.0）も動きます。`ollama` プロファイルでは Ollama（MIT）も動きます。

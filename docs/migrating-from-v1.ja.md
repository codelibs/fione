# v1 から v2 への移行

Fione v2 は、v1 の考え方（ブラウザで CSV からモデルを作り、予測 API まで出す）と主な流れ（アップロード → データ分析 → 実行 → 予測結果サマリー → 予測・サービング）を引き継いだ、新しい実装です。
English: [Moving from Fione v1 to v2](migrating-from-v1.md)

## 変わったこと

| | v1 | v2 |
|---|---|---|
| 動作形態 | Fess のプラグイン（Java、LastaFlute） | 単独のサーバー（Python、FastAPI）。Fess・Elasticsearch は不要 |
| AutoML エンジン | H2O | Fione 独自のエンジン。LightGBM・XGBoost・CatBoost・scikit-learn の ExtraTrees を Optuna で調整し、アンサンブルします |
| ストレージ | MinIO（JSON とファイル） | データとモデルは SeaweedFS などの S3 互換ストレージ、ユーザー・プロジェクト・ジョブ・モデルの記録は SQLite |
| 起動 | Fess と H2O を別々に用意 | `docker compose up`（Fione と SeaweedFS） |
| ユーザーとロール | Fess のユーザーに `admin-easyml`・`admin-automl`・`admin-systemml` のロールを付け、使える画面もロールで決まる | Fione 独自のユーザーに **admin**・**editor**・**viewer** のいずれか 1 つのロールを付けます。プロジェクトごとにオーナーがいて、ほかのユーザーに編集者または閲覧者として共有できます。簡易表示と詳細表示は権限ではなく、表示の好みです |
| サービング | Dockerfile・`fione-serving.jar`・H2O の MOJO を含む zip を `docker build` | モデルのファイルと共通の `fione-serving` イメージを `docker run`（[Fione Serving](serving.md)、英語） |
| Python モジュール | H2O の Python API 向けのスクリプト | pandas の DataFrame を受け取って返す、新しい簡単な API（[下記](#python-モジュール)） |
| 自動化 | サービング以外の API なし | `/api/v1` の REST API と API トークン（OpenAPI は `/api/docs`） |

## 引き継がれないもの

- **H2O のモデルは移行できません。** H2O 独自の形式のため、v2 で学習し直してください。
- **v1 のデータは読み込みません。** v1 の MinIO のバケットは使いません。CSV をアップロードし直して学習してください。
- **ユーザーは移行されません。** 管理者が「ユーザー」画面で作り直します。
- **Python モジュールは書き直しが必要です。**（新しい API に合わせます）
- **H2O Flow、Rapids、MOJO / genmodel のダウンロードはなくなりました。** Flow の後継として Notebook 連携を予定しています。データ操作は pandas ベースのモジュールで行います。

## 用語

画面の用語は v1 のものを引き継いでいます。

| 日本語 | English（v2 の画面） |
|---|---|
| プロジェクト | Project |
| データ分析 | Data analysis |
| 予測する列（何を予測しますか？） | Column to predict |
| 入力する列 | Input columns |
| 最大実行時間 | Maximum run time |
| 実行 | Run |
| 予測結果サマリー | Prediction summary |
| Fione 君 | Fione-kun |
| 学習データ / 予測するデータ / 予測結果 | Training data / Data to predict / Predictions |
| ジョブ | Job |

## 機能ごとの対応

| v1 の機能 | v2 |
|---|---|
| プロジェクトの作成・削除 | あり |
| データセット（学習・テスト・予測）、CSV のアップロード・ダウンロード | あり |
| フレームのパース・型変更・エクスポート・保存 | あり（アップロード時に CSV を Parquet に変換。データ変換は Python モジュール） |
| 列ビュー、データビュー、列ごとの EDA | あり。欠損、相関、外れ値、リークの疑い、型の推定を追加 |
| EasyML ウィザード、AutoML 画面 | あり（簡易表示と詳細表示） |
| AutoML の実行とパラメータ（fold 数、クラスの均等化、シード、最大モデル数・最大実行時間、モデルごとの時間、停止条件、ソート指標、CV 予測・モデル・fold 割当の保持、除外列） | あり |
| ジョブ一覧・削除・全削除・キャンセル | あり |
| リーダーボード、モデル詳細（重要度、スコア履歴、CV 指標） | あり |
| モデルのエクスポート・インポート・全モデルのエクスポート | あり（インポートは管理者のみ） |
| バッチ予測（予測結果をデータセットとして保存） | あり |
| 予測結果サマリー（最良モデル、星評価、Fione 君） | あり |
| サービング用 zip | サービング用ファイルと共通イメージに置き換え |
| MOJO / genmodel のダウンロード | 廃止。可能な範囲での ONNX 出力を予定 |
| H2O Flow | 廃止。Notebook 連携（JupyterLab）を**予定** |
| Rapids | 廃止（pandas ベースのモジュール） |
| Python モジュール: フレーム操作（cbind、concat、cor、cslice、fillna、floor、pivot、rbind、replace、rslice、sort、split、tokenize） | 組み込みモジュールとしてあり |
| Python モジュール: kmeans の学習・予測 | あり（scikit-learn の KMeans） |
| Python モジュール: glrm の学習・予測 | `lowrank_train` / `lowrank_predict`（scikit-learn の TruncatedSVD / NMF）に置き換え |
| Python モジュール: word2vec | なし。テキストの埋め込みモジュールを予定 |
| モジュールのアップロード・リロード | あり。管理者のみ、警告付き（モジュールはサンドボックスで動きません） |
| systemml 画面（H2O の状態、クラスタの停止） | 「**システムの状態**」画面（ジョブ、ストレージ、ワーカー）に置き換え |
| 3 つのロール、ユーザー別のセッション | 作り直し: admin / editor / viewer とプロジェクトの共有 |
| 日本語と英語 | あり |

**この版には含まれず、予定しているもの**：Notebook 連携（JupyterLab と Python SDK）、SHAP と部分依存、LLM アシスタント（Ollama。Mac では既定で `gemma4:12b-mlx`）、MCP サーバー、ONNX 出力。

## Python モジュール

v2 のモジュールは、`MODULE` の説明と `run` 関数を持つ 1 つの Python ファイルです。フレーム操作の例:

```python
MODULE = {"name": "Add one", "kind": "frame", "params": {"type": "object", "properties": {}}}


def run(df, params, ctx):
    return df + 1
```

`run` は pandas の DataFrame とパラメータ（`params` の JSON スキーマで検査済み）を受け取り、DataFrame を返します。管理者が「**Python モジュール**」画面か `POST /api/v1/modules` でアップロードし、`POST /api/v1/projects/{id}/jobs/module` のジョブで実行します。アップロードしたモジュールはサンドボックスなしで、サーバーと同じ権限でジョブのワーカー内で動きます。信頼できるコードだけをアップロードしてください。

## REST API

v1 にはサービング以外の公開 API がありませんでした。v2 の API は `/api/v1` の下にあり、OpenAPI の文書は `/api/docs` です。スクリプトは「**アカウント**」画面で作った API トークンを `Authorization: Bearer <トークン>` で送ります。トークンは発行したユーザーとして、そのユーザーのロールとプロジェクトの範囲で動きます。

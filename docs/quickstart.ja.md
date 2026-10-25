# クイックスタート

Docker だけで、Fione を起動してモデルを作り、予測ファイルを作り、予測 API を動かすまでの手順です。
English: [Quick start](quickstart.md)

## 必要なもの

- Docker と Compose v2（Docker Desktop、または compose プラグイン付きの Docker Engine）
- イメージとビルドキャッシュ用に約 6 GB のディスク容量と、データを置く容量
- `git`、`openssl`、`unzip`、`curl`
- 新しめのブラウザ：Chrome / Edge 123 以降、Firefox 120 以降、Safari 17.5 以降（それより古いブラウザではライトテーマのみ）

イメージはこのリポジトリから手元でビルドします。amd64 と arm64（Apple シリコン）のどちらでも動きます。

## 1. 取得と秘密情報の設定

```sh
git clone https://github.com/codelibs/fione.git
cd fione
printf 'FIONE_S3_ACCESS_KEY=%s\nFIONE_S3_SECRET_KEY=%s\n' "$(openssl rand -hex 16)" "$(openssl rand -hex 32)" > docker/.env
```

`docker/.env` には、Fione とストレージ（SeaweedFS）が共有する認証情報が入ります。git の管理対象外です。他人に見せないでください。ほかに設定できる値は `docker/.env.example` にあります（[設定](configuration.md)、英語）。

## 2. 起動

```sh
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
```

初回のビルドでは機械学習ライブラリを取得するため、数分かかります。`--wait` は 2 つのコンテナが正常に動き出すまで待ちます。起動後は <http://127.0.0.1:8080/> で開けます（このマシンからのみ。ほかのマシンに公開する方法は[設定](configuration.md#behind-a-reverse-proxy)を参照）。

## 3. 管理者の作成

Fione には既定のパスワードがありません。初回起動時に、一度だけ使うセットアップトークンをログに出力します。

```sh
docker compose -f docker/compose.yaml --env-file docker/.env logs fione | grep "Setup token"
```

<http://127.0.0.1:8080/> を開くと「**管理者アカウントの作成**」画面になります。**セットアップトークン**、**管理者のユーザー名**、**パスワード**（8 文字以上、確認用にもう一度）を入力し、「**管理者を作成**」を押すと、そのままログインした状態になります。

管理者ができるまでは、ログインを読める人なら誰でも管理者を作れます。初回起動後は早めに作成してください。

## 4. 試す CSV の用意

見出し行のある CSV なら何でも使えます。定番のアヤメ（iris）で試す場合は、起動中のコンテナから scikit-learn 同梱のデータを書き出します。

```sh
docker compose -f docker/compose.yaml --env-file docker/.env exec -T fione python -c "from sklearn.datasets import load_iris; d = load_iris(as_frame=True); f = d.frame; f['species'] = d.target_names[f.pop('target')]; f.to_csv('/dev/stdout', index=False)" > iris.csv
```

`iris.csv`（150 行、4 つの計測値と `species` 列）ができます。

## 5. モデルを作る（EasyML）

1. 「**プロジェクト**」画面の「**新しいプロジェクト**」に名前（例：`Iris`）を入力して「**プロジェクトを作成**」を押し、そのプロジェクトを開きます。
2. 「**学習データをアップロード**」を押し、`iris.csv` を選んで「**アップロードして分析**」を押します。
3. 「**データ分析**」画面に各列の情報が出ます。Fione が**予測する列**（「何を予測しますか？」：`species`）、**予測の種類**（分類）、**入力する列**を提案します。答えをそのまま含む列や行を識別するだけの列は、理由付きでチェックが外れています。
4. 「**最大実行時間**」で「**1 分**」を選び、「**実行**」を押します。
5. 進行状況の画面で、いま何を試しているかが見えます。学習が終わると「**予測結果サマリー**」が開きます。最良のモデル、1〜5 の星による評価、スコアの意味の説明、**Fione 君**のひと言が表示されます。

## 6. 予測する

サマリーの「**予測する**」を押し、同じ入力列を持つ CSV を選んで「**アップロード**」を押します（予測する列は不要です。`iris.csv` でも試せます）。予測と並べて残す列を選んで「**予測を実行**」を押すと、結果画面に先頭の行が表示され、`predict_<名前>.csv` をダウンロードできます。予測したクラスの `predict` 列と、クラスごとの確率の `p_<クラス>` 列が付きます。

## 7. 予測 API を動かす（Fione Serving）

サマリーの「**自分のシステムで使う**」で「**サービング用ファイルをダウンロード**」を押すと、モデルのファイル（zip）が手に入り、実行する `docker run` コマンドが表示されます。サービング用イメージは最初に一度ビルドします（モデルは Fione と同じタグのイメージでしか動きません）。

```sh
docker compose -f docker/compose.yaml --env-file docker/.env --profile serving build fione-serving
```

zip をダウンロードしたディレクトリで:

```sh
unzip fione-serving-*.zip
docker run --rm -p 8081:8080 -v "$PWD/model:/model:ro" ghcr.io/codelibs/fione-serving:dev
```

別のターミナルから:

```sh
curl -s -X POST localhost:8081/invocations -H 'Content-Type: application/json' -d '{"instances":[{"sepal length (cm)":5.1,"sepal width (cm)":3.5,"petal length (cm)":1.4,"petal width (cm)":0.2}]}'
```

```json
{"predictions":[{"label":"setosa","index":0,"class_probabilities":[0.9934803442259019,0.003455065889847104,0.0030645898842508773]}]}
```

Ctrl+C で止まります。API の詳細は [Fione Serving](serving.md)（英語）を参照してください。

## ウィザードの先へ

右上のアカウントメニュー（ユーザー名）で「**表示**」を「**詳細**」にすると、AutoML の画面が使えます。列ごとの統計とグラフ、学習の全設定、ジョブ一覧、リーダーボード・変数重要度・スコア履歴付きのモデル画面、モデルのエクスポートとインポート、プロジェクトの共有です。管理者は同じメニューから、ユーザー、Python モジュール、システムの状態も管理できます。

## 停止・バックアップ・更新

停止します（データは Docker ボリューム `fione_fione-data` と `fione_seaweed-data` に残ります）。

```sh
docker compose -f docker/compose.yaml --env-file docker/.env down
```

`down -v` にするとボリュームも削除され、プロジェクト・モデル・ユーザーがすべて消えます。

停止中に、現在のディレクトリへ 2 つのアーカイブとしてバックアップします。

```sh
docker run --rm -u 0 -v fione_fione-data:/data:ro --entrypoint tar ghcr.io/codelibs/fione:dev czf - -C /data . > fione-data.tgz
docker run --rm -u 0 -v fione_seaweed-data:/data:ro --entrypoint tar ghcr.io/codelibs/fione:dev czf - -C /data . > seaweed-data.tgz
```

`fione-data.tgz` にはデータベースと秘密鍵が入っています。厳重に保管してください。`docker/.env` はアーカイブに含まれないので、一緒に保管するか、手順 1 の `printf` で作り直してください。

空のボリュームへ戻すには（新しいマシンで初回起動の前など）、イメージをビルドしてから戻し、通常どおり起動します（Compose がボリュームは既にあると警告しますが、問題ありません）。

```sh
docker compose -f docker/compose.yaml --env-file docker/.env build
docker run --rm -i -u 0 -v fione_fione-data:/data --entrypoint tar ghcr.io/codelibs/fione:dev xzf - -C /data < fione-data.tgz
docker run --rm -i -u 0 -v fione_seaweed-data:/data --entrypoint tar ghcr.io/codelibs/fione:dev xzf - -C /data < seaweed-data.tgz
```

更新するときは、バックアップし、今のサービング用イメージを別の名前で残してから（ビルドし直すと `ghcr.io/codelibs/fione-serving:dev` が置き換わるため）、新しい版を取得してビルドし直します。

```sh
docker tag ghcr.io/codelibs/fione-serving:dev fione-serving:before-upgrade
git pull
docker compose -f docker/compose.yaml --env-file docker/.env up -d --build --wait
```

データはそのまま残ります。古い版で学習したモデルが新しい版で読み込める保証はありません（Fione のコードの pickle のため）。頼りにしているモデルは更新後に学習し直してください。それまでは、`docker run` コマンドの `ghcr.io/codelibs/fione-serving:dev` を `fione-serving:before-upgrade` に置き換えて、残したイメージで配信できます（版ごとに `docker/.env` の `FIONE_IMAGE_TAG` を変えておけば、両方のイメージのタグに版が入るので、この手間は不要です）。

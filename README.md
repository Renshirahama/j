# ジャグラー狙い台分析システム MVP

パチスロの次回ボーナスを予言するものではありません。過去の台別実績から、翌日の候補台を統計的スコアとしてランキングし、walk-forwardバックテストでランダム選択と比較します。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Web UI:

```bash
cd web
npm install
npm run dev
```

## データの入れ方

自動取得は`src/collectors/slonavi_importer.py`にadapterを用意しています。実行時に`robots.txt`を確認し、禁止されているURLなら停止します。接続できない、または許可が確認できない場合はCSVインポートを使います。

スロナビURL単発:

```bash
PYTHONPATH=src python -m juggler_analysis.cli import-slonavi-url https://slo-navi.com/data/2026-08-26-11297/ --date 2026-08-26
```

スロナビ日付範囲:

```bash
PYTHONPATH=src python -m juggler_analysis.cli import-slonavi-range --start 2026-06-01 --end 2026-08-31
```

範囲取得は`config/sources.yaml`の`request_delay_seconds`を挟みます。短時間に大量アクセスする用途にはしないでください。

この環境のように`robots.txt`へ接続できず許可確認できない場合、コマンドはデータページを取得せず停止します。ブラウザで通常表示でき、利用規約上も問題ない範囲でHTMLを保存できる場合は、保存済みHTMLを解析できます。

```bash
PYTHONPATH=src python -m juggler_analysis.cli parse-slonavi-html data/raw/slonavi/2026-08-26.html --date 2026-08-26
```

CSVインポートの必須カラム:

```csv
date,machine_name,machine_number,games,bb,rb,difference_medals
2026-08-01,マイジャグラーV,2184,8123,31,29,1250
```

任意カラム:

```text
combined_probability,bb_probability,rb_probability,store_total_difference,store_average_difference,store_average_games,store_win_rate
```

## DB作成方法

```bash
PYTHONPATH=src python -m juggler_analysis.cli init-db
```

## サンプルデータ

実データがない状態でも動作確認できます。

```bash
PYTHONPATH=src python -m juggler_analysis.cli generate-sample
PYTHONPATH=src python -m juggler_analysis.cli import-csv data/raw/sample_my_juggler_v.csv
```

## 分析実行方法

ランキング確認:

```bash
PYTHONPATH=src python -m juggler_analysis.cli rank --top 10
```

## バックテスト方法

ダッシュボードJSON生成時に、30日目以降をwalk-forwardで検証します。

```bash
PYTHONPATH=src python -m juggler_analysis.cli export-dashboard
```

出力:

```text
web/public/dashboard.json
```

## Webアプリ起動方法

```bash
cd web
npm install
npm run dev
```

スマホから同一LANで見る場合は、Next.jsの表示するNetwork URLを開いてください。

## 設定

店舗・機種:

```text
config/store.yaml
```

特定日:

```text
config/special_days.yaml
```

高設定らしいproxy label:

```text
config/labels.yaml
```

## テスト

```bash
PYTHONPATH=src pytest
```

対象:

```text
確率計算、rolling特徴量、前日特徴量、future leakage防止、ランキング、バックテスト
```

## 注意

自動取得は公開HTML表を通常アクセスで読むだけです。ログイン、CAPTCHA、アクセス制限、ブロック、非公開APIの回避はしません。サイト側の利用規約で禁止されている場合は使用しないでください。

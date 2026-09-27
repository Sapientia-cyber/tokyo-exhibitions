# 東京美術館 会期表

東京の主要館の展覧会を、**会期のガントチャート**と**一覧表**で横断的に見るページ。
GitHub Actions が毎朝データを取得してコミットし、**Cloudflare Pages** がその push を
検知してビルド・公開する。**Basic認証でパスワードをかけているので、公開URLでも
パスワードを知っている人しか見られない。**

```
会期表
├── data/exhibitions.json      ← 唯一のデータ。Actions がここを更新する
├── scraper/
│   ├── museums.py             ← 館の設定表（ここだけ直せば大体なんとかなる）
│   ├── fetch.py               ← 汎用抽出器 + 取得オーケストレーション
│   └── requirements.txt
├── site/
│   ├── template.html          ← アプリ本体（__DATA__ を埋める）
│   ├── build.py               ← template + json → dist/（標準ライブラリのみ）
│   └── *.png                  ← ホーム画面用アイコン
├── functions/
│   └── _middleware.js         ← Cloudflare Pages Functions。全ページに Basic認証をかける
├── .python-version            ← ビルドが読む Python のバージョン
├── .gitattributes             ← 改行コードを LF に固定（Windows対策）
├── .gitignore
└── .github/workflows/update.yml
```
毎朝5時（日本時間）に1本のワークフローが走る。

    収集 (Playwright) → data/exhibitions.json を更新・コミット
                      → (Cloudflare Pages が push を検知)
                      → site/build.py で dist/ を生成 → 公開

データの取得はGitHub側、ビルドと公開はCloudflare側、という役割分担。
リポジトリ自体は公開（public）のままだが、**サイトの閲覧にはパスワードが必要**。

## セットアップ

### 1. GitHubにpush

```bash
git init && git add -A
git commit -m "初期コミット"
git remote add origin git@github.com:<あなた>/tokyo-exhibitions.git
git push -u origin main
```

### 2. Cloudflare Pages にこのリポジトリをつなぐ

Cloudflare ダッシュボード → **Workers & Pages** → **Create** → **Pages** →
**Connect to Git** でこのリポジトリを選ぶ。

| 項目 | 値 |
|---|---|
| Framework preset | None |
| Build command | `python3 site/build.py` |
| Build output directory | `dist` |

「Save and Deploy」で初回デプロイが走る。完了すると
`https://tokyo-exhibitions-xxx.pages.dev` のようなURLが発行される
（あとで自分のドメインに変えることもできる）。

### 3. パスワードをかける

Cloudflare ダッシュボード → このPagesプロジェクト → **Settings** →
**Environment variables** で、次の2つを **Secret**（暗号化）として追加する。

| 変数名 | 値 |
|---|---|
| `SITE_USER` | 好きなユーザー名（例: `tokyo`） |
| `SITE_PASSWORD` | 好きなパスワード |

追加したら **Deployments** タブ → 最新のデプロイの「…」→
**Retry deployment** でもう一度デプロイし直す（環境変数は次のデプロイから
効くため）。以降、サイトを開くとブラウザ標準のID・パスワード入力画面が出る。

> `functions/_middleware.js` がこの認証をやっている。`SITE_USER` /
> `SITE_PASSWORD` のどちらかが未設定のままだと**認証なし（誰でも見える）**
> になるので、設定を忘れないこと。

### 4. GitHub Actions を初回実行

**Actions** タブ →「会期データ更新」→ **Run workflow**。

実行結果のサマリに館ごとの件数と「0件だった館」が出るので、そこを確認する。
コミットが発生すると Cloudflare Pages が自動でビルド・再デプロイする。

以降は毎朝5時（日本時間）に自動で回る。

> スケジュール実行は、リポジトリが60日間まったく動きがないと GitHub 側で
> 自動停止される。停止したらActionsタブから再度有効化する。

### 5. iPhoneのホーム画面に置く

発行されたURL（`.pages.dev`）をSafariで開き、ID・パスワードを入力。
共有ボタン →「ホーム画面に追加」。manifest とアイコンを同梱してあるので、
アドレスバーなしの全画面で起動する。

> パスワード入力はSafariが記憶してくれるので、ホーム画面アイコンからの
> 起動では毎回聞かれるわけではない（Safariの設定次第）。

## ローカルで動かす

```bash
pip install -r scraper/requirements.txt
python -m playwright install chromium

python scraper/fetch.py --dry-run        # 取得して差分だけ見る
python scraper/fetch.py                  # data/exhibitions.json を更新
python site/build.py                     # dist/ を生成
open dist/index.html
```

`site/build.py` は標準ライブラリしか使わないので、`pip install` なしでも動く。
（`functions/_middleware.js` はCloudflare Pages上でのみ動作し、ローカルの
`dist/index.html` を直接開いたときには関与しない）

## 取得の仕組み

館ごとにCSSセレクタを書くと、サイト改修のたびに全部直すことになる。
そこで抽出器は1つだけ持ち、**「詳細ページへのリンク」＋「その周辺テキストに
会期らしき日付範囲があるか」**だけを手がかりにしている。
館ごとの違いは `museums.py` の4項目に押し込んである。

| 項目 | 役割 |
|---|---|
| `list_url` | 展覧会一覧ページ |
| `mode` | `http` = requests で取れる / `js` = Playwright が必要 |
| `link` | 詳細ページへのリンクを見分ける正規表現 |
| `cat` | 種別（特別展／企画展／コレクション展／小企画）の判定ルール |

`js` にしてある館は、requests だと中身が空で返るか 403 を返す館
（東京国立博物館、サントリー美術館、三菱一号館美術館、東京都現代美術館、
SOMPO美術館 など）。Playwright が実ブラウザでレンダリングしてから読む。

### 壊れたときの直し方

| 症状 | 見るところ |
|---|---|
| 0件になった | `list_url` が生きているか確認 → だめなら `mode` を `js` に |
| 変な行が混ざる | `link` の正規表現をきつくする |
| 会期がずれる | `fetch.py` の `parse_range()` にその表記のテストを足す |

1館だけ詳しく見たいとき:

```bash
python scraper/fetch.py --debug mot
```

拾った候補と、捨てた候補（`skip(title)`）が全部出る。

### 壊れても表は空にならない

- 取得に失敗した館は、**既存データをそのまま温存**する
- 全館失敗したときだけ Actions が赤くなる（静かに空データを配信しないため）
- 終了から60日を過ぎた展覧会は自動で捨てる（`--keep-days` で変更可）

つまり公開されているのは常に **「最後に成功したデータ」**。
スクレイピングが全部壊れても、サイトが落ちたり空になったりはしない。

### 相手のサーバへの配慮

アクセス間隔は2〜4秒、実行は1日1回。館を増やすときもこの前提は崩さないこと。
各サイトの robots.txt と利用規約の確認は各自の責任で。

## 館を増やす

`museums.py` に1件足すだけ。`id` は一度決めたら変えない
（`data/exhibitions.json` の `venue` と対応しているため）。

```python
dict(id="setagaya", name="世田谷美術館", short="世田谷", area="世田谷区", station="用賀",
     site="https://www.setagayaartmuseum.or.jp/",
     list_url="https://www.setagayaartmuseum.or.jp/exhibition/",
     mode="http", link=r"/exhibition/", cat={}, default_cat="企画展"),
```

足したら `--debug setagaya` で拾えているか確認する。

## 全国展開するとき

`museums.py` に `pref`（都道府県）を足し、`site/template.html` の
エリアフィルタを区→都道府県に切り替える。館が100を超えたら、
ガントの行を会場単位から都市単位に畳む切り替えがほしくなるはず。

## データの形

```jsonc
{
  "generatedAt": "2026-09-12",
  "venues":      [{ "id": "nact", "name": "国立新美術館", "area": "港区", ... }],
  "exhibitions": [{
    "venue": "nact",                  // venues[].id
    "title": "ルーヴル美術館展 ルネサンス",
    "start": "2026-09-09",            // ISO 8601
    "end":   "2026-12-13",
    "category": "企画展",              // 特別展 / 企画展 / コレクション展 / 小企画 / 特集展示
    "url": "https://www.nact.jp/..."
  }]
}
```
## 免責

会期は公式サイトからの機械収集。休館日・会期変更・展示替えは反映されない。
来館前に必ず公式ページで確認すること。

## セキュリティについて

- `functions/_middleware.js` によるBasic認証は、**個人利用や家族・友人内での
  共有には十分な強さ**だが、`SITE_USER`/`SITE_PASSWORD` は平文でブラウザに
  送られる（TLSで暗号化はされる）。より強いアクセス制御（メールでのログイン等）
  が欲しくなったら、Cloudflare **Zero Trust → Access** でアプリケーションを
  登録する方法に切り替えられる（`_middleware.js` は不要になる）。
- リポジトリ自体（GitHubの`data/exhibitions.json`やコード）は公開のままなので、
  非公開にしたい情報は置かないこと。

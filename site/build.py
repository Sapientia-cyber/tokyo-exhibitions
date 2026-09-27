#!/usr/bin/env python3
"""
site/template.html に data/exhibitions.json を埋め込んで dist/ を作る。

    python site/build.py

テンプレート内の __DATA__ を JSON に置き換え、アイコンと _headers を並べるだけ。
ビルドツールも依存パッケージも使わない（標準ライブラリのみ）。
Cloudflare Pages のビルドコマンドにそのまま指定できる。
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "site" / "template.html"
DATA = ROOT / "data" / "exhibitions.json"
DIST = ROOT / "dist"

HEAD = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#FCFBF8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#16181A" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="会期表">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="description" content="東京の主要美術館の展覧会を、会期のガントチャートと一覧表で横断的に見る。">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" href="icon-192.png" sizes="192x192">
<link rel="manifest" href="manifest.webmanifest">
<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""
FOOT = "\n</body>\n</html>\n"

# 参照はすべて相対パスにしてある。GitHub Pages のプロジェクトページは
# https://<user>.github.io/<repo>/ のようにサブパス配信になるため、
# 絶対パス（/icon-192.png）だと 404 になる。相対なら独自ドメインでも
# Cloudflare Pages でも同じまま動く。
MANIFEST = {
    "name": "東京美術館 会期表",
    "short_name": "会期表",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#FCFBF8",
    "theme_color": "#FCFBF8",
    "lang": "ja",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}

# index.html は毎日変わるのでキャッシュさせない。アイコンは不変なので長く持たせる。
# これは Cloudflare Pages 用の書式。GitHub Pages では無視される（置いても無害なので、
# あとで Cloudflare に移すときのために残してある）。
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

/
  Cache-Control: public, max-age=0, must-revalidate

/index.html
  Cache-Control: public, max-age=0, must-revalidate

/exhibitions.json
  Cache-Control: public, max-age=300

/*.png
  Cache-Control: public, max-age=31536000, immutable
"""

STATIC = ["apple-touch-icon.png", "icon-192.png", "icon-512.png"]


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    tpl = TPL.read_text(encoding="utf-8")
    if "__DATA__" not in tpl:
        print("template.html に __DATA__ が見つかりません", file=sys.stderr)
        return 1

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    page = HEAD + tpl.replace("__DATA__", payload) + FOOT

    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    # 生データも一緒に置いておく（他から参照したくなったとき用）
    (DIST / "exhibitions.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DIST / "manifest.webmanifest").write_text(
        json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")

    for name in STATIC:
        src = ROOT / "site" / name
        if src.exists():
            shutil.copy2(src, DIST / name)
        else:
            print(f"  ! {name} が見つかりません（アイコンなしで続行）", file=sys.stderr)

    n = len(data.get("exhibitions", []))
    print(f"  → dist/index.html ({len(page):,} bytes, 展覧会 {n}件, "
          f"更新日 {data.get('generatedAt')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

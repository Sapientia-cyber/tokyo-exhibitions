#!/usr/bin/env python3
"""
東京主要館の展覧会会期を収集して data/exhibitions.json を更新する。

    python scraper/fetch.py                  # 全館
    python scraper/fetch.py --only nact mot  # 指定館のみ
    python scraper/fetch.py --dry-run        # 差分を出すだけ
    python scraper/fetch.py --debug nact     # 1館ぶん、拾った候補を全部出す

取り方の考え方
--------------
館ごとにCSSセレクタを書くと、サイト改修のたびに全部直すことになる。
ここでは「詳細ページへのリンク」＋「その周辺テキストに会期らしき日付範囲があるか」
だけを手がかりにする、汎用の抽出器を1つ持つ方式にしている。
館ごとの違いは museums.py の設定（list_url / mode / link / cat）に押し込む。

  - ノイズを拾ったら → museums.py の link をきつくする
  - 0件になったら   → list_url が変わっていないか確認、次に mode を "js" にしてみる

取得できなかった館のデータは消さずに温存する。1館の失敗で表全体が空になるのが
一番困るため。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from museums import MUSEUMS, BY_ID  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "exhibitions.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
DELAY = (2.0, 4.0)      # アクセス間隔（秒）。相手のサーバに迷惑をかけない
TIMEOUT = 25

# ------------------------------------------------------------------ 会期パース

JP_DATE = re.compile(r"(?:(\d{4})\s*年)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
SLASH = re.compile(r"(?:(\d{4})\s*[./]\s*)?(\d{1,2})\s*[./]\s*(\d{1,2})")
DASH = re.compile(r"\s*[〜~～‐-―\-–—―]\s*")
PAREN = re.compile(r"[（(][^）)]{0,12}[）)]")


def parse_range(text: str, base_year: int | None = None):
    """'2026年9月9日(水)〜12月13日(日)' -> (date, date) / 見つからなければ None"""
    if not text:
        return None
    base_year = base_year or dt.date.today().year
    t = PAREN.sub("", text)
    t = t.replace("開催期間", " ").replace("会期", " ")
    parts = DASH.split(t)
    if len(parts) < 2:
        return None

    # 「…9月9日 〜 12月13日…」の左右それぞれで最も後ろ／前の日付を拾う
    left, right = parts[0], parts[1]
    m1 = _last(JP_DATE, left) or _last(SLASH, left)
    m2 = _first(JP_DATE, right) or _first(SLASH, right)
    if not m1 or not m2:
        return None
    try:
        y1, mo1, d1 = m1.groups()
        start = dt.date(int(y1 or base_year), int(mo1), int(d1))
        y2, mo2, d2 = m2.groups()
        end = dt.date(int(y2 or start.year), int(mo2), int(d2))
        if end < start:                       # 年跨ぎ（12月〜1月 など）
            end = end.replace(year=end.year + 1)
    except ValueError:
        return None
    if not (dt.date(2000, 1, 1) <= start <= dt.date(2100, 1, 1)):
        return None
    if (end - start).days > 800:              # 明らかにおかしい範囲は捨てる
        return None
    return start, end


def _last(pat, s):
    ms = list(pat.finditer(s))
    return ms[-1] if ms else None


def _first(pat, s):
    return pat.search(s)


# ------------------------------------------------------------------ 取得

def sleep():
    time.sleep(random.uniform(*DELAY))


def get_http(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA,
                                   "Accept-Language": "ja,en;q=0.8"},
                     timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    sleep()
    return r.text


_browser = None


def get_js(url: str) -> str:
    """Playwright でレンダリング後のHTMLを返す。JS描画・403対策。"""
    global _browser
    from playwright.sync_api import sync_playwright

    if _browser is None:
        _browser = sync_playwright().start()
    b = _browser.chromium.launch()
    try:
        ctx = b.new_context(user_agent=UA, locale="ja-JP",
                            viewport={"width": 1280, "height": 1800})
        p = ctx.new_page()
        p.goto(url, wait_until="networkidle", timeout=45000)
        p.wait_for_timeout(1200)
        # 遅延読み込みの一覧に備えて一度スクロールする
        p.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        p.wait_for_timeout(800)
        html = p.content()
    finally:
        b.close()
    sleep()
    return html


# ------------------------------------------------------------------ 抽出

NOISE = re.compile(
    r"^(過去の|これまでの|次回|今後|一覧|もっと|詳細|チケット|アクセス|ホーム|"
    r"English|BACK|MORE|READ|VIEW|PAST|CURRENT|UPCOMING)", re.I)
STRIP_LABEL = re.compile(r"^(特別展|企画展|展覧会|開催中|会期中|NEW|New)\s*[:：]?\s*")


def clean_title(text: str) -> str:
    t = PAREN.sub("", text)
    t = re.split(r"\d{4}\s*年\s*\d{1,2}\s*月", t)[0]
    t = re.split(r"\d{1,2}\s*月\s*\d{1,2}\s*日", t)[0]
    t = re.split(r"\d{4}[./]\d{1,2}[./]\d{1,2}", t)[0]
    t = STRIP_LABEL.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" 　|｜/・-—–")
    return t


def categorize(cfg: dict, href: str, text: str) -> str:
    for pat, cat in (cfg.get("cat") or {}).items():
        if re.search(pat, href) or re.search(pat, text):
            return cat
    return cfg.get("default_cat", "企画展")


def harvest(html: str, cfg: dict, debug: bool = False) -> list[dict]:
    """リンク＋周辺テキストから (タイトル, 会期) を拾う汎用抽出器。"""
    soup = BeautifulSoup(html, "html.parser")
    link_re = re.compile(cfg["link"])
    base = cfg["list_url"]
    found: dict[tuple, dict] = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not link_re.search(href):
            continue

        anchor_text = a.get_text(" ", strip=True)
        # アンカー自身 → 親 → 祖父 と窓を広げながら会期を探す
        node, window, rng = a, anchor_text, None
        for _ in range(3):
            rng = parse_range(window)
            if rng:
                break
            node = node.parent
            if node is None:
                break
            window = node.get_text(" ", strip=True)
            if len(window) > 600:      # 広げすぎて別の展覧会の日付を拾う前に打ち切る
                break
        if not rng:
            continue

        title = clean_title(anchor_text) or clean_title(window)
        if len(title) < 4 or NOISE.match(title):
            if debug:
                print(f"    skip(title): {title!r} <- {anchor_text[:40]!r}")
            continue

        key = (title, str(rng[0]))
        if key in found:
            continue
        found[key] = dict(
            title=title,
            start=str(rng[0]),
            end=str(rng[1]),
            category=categorize(cfg, href, window),
            url=urljoin(base, href),
        )
        if debug:
            print(f"    ok: {rng[0]}〜{rng[1]}  {title}")

    return sorted(found.values(), key=lambda e: (e["start"], e["title"]))


def fetch_one(cfg: dict, debug: bool = False) -> list[dict]:
    html = get_js(cfg["list_url"]) if cfg["mode"] == "js" else get_http(cfg["list_url"])
    rows = harvest(html, cfg, debug)
    # http で0件なら一度だけ JS で再挑戦（静的だと思っていたが動的化された場合）
    if not rows and cfg["mode"] == "http":
        if debug:
            print("    http で0件 → JS で再試行")
        rows = harvest(get_js(cfg["list_url"]), cfg, debug)
    return rows


# ------------------------------------------------------------------ 出力

def build_venues() -> list[dict]:
    return [dict(id=m["id"], name=m["name"], short=m["short"], area=m["area"],
                 station=m["station"], url=m["site"]) for m in MUSEUMS]


def load_existing() -> dict:
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {"generatedAt": str(dt.date.today()), "region": "東京",
            "venues": build_venues(), "exhibitions": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="対象の館ID")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--debug", metavar="ID", help="1館だけ詳細ログ付きで実行")
    ap.add_argument("--keep-days", type=int, default=60,
                    help="終了後この日数を過ぎた展覧会は捨てる（既定60日）")
    args = ap.parse_args()

    if args.debug:
        cfg = BY_ID.get(args.debug)
        if not cfg:
            print(f"未知の館ID: {args.debug}", file=sys.stderr)
            return 1
        print(f"[{cfg['name']}] {cfg['list_url']} mode={cfg['mode']}")
        for r in fetch_one(cfg, debug=True):
            print("   ", r)
        return 0

    data = load_existing()
    old = data.get("exhibitions", [])
    targets = args.only or [m["id"] for m in MUSEUMS]

    fetched: dict[str, list[dict]] = {}
    failed: list[str] = []

    for vid in targets:
        cfg = BY_ID.get(vid)
        if not cfg:
            print(f"  ! 未知の館ID: {vid}", file=sys.stderr)
            continue
        try:
            rows = fetch_one(cfg)
            if not rows:
                raise RuntimeError("0件（link 正規表現か list_url を見直す）")
            fetched[vid] = rows
            print(f"  ✓ {cfg['name']}: {len(rows)}件")
        except Exception as e:
            failed.append(vid)
            print(f"  ✗ {cfg['name']}: {type(e).__name__}: {e}", file=sys.stderr)

    kept = [e for e in old if e.get("venue") not in fetched]
    merged = kept + [dict(venue=vid, **r) for vid, rows in fetched.items() for r in rows]

    cutoff = dt.date.today() - dt.timedelta(days=args.keep_days)
    merged = [e for e in merged if e["end"] >= str(cutoff)]
    merged.sort(key=lambda e: (e["start"], e["venue"], e["title"]))

    print(f"\n  旧 {len(old)}件 → 新 {len(merged)}件"
          f"　（更新 {len(fetched)}館 / 失敗 {len(failed)}館）")
    if failed:
        print(f"  データを温存した館: {', '.join(BY_ID[v]['name'] for v in failed)}")

    if args.dry_run:
        print("  --dry-run のため書き込みませんでした")
        return 0

    data["venues"] = build_venues()
    data["exhibitions"] = merged
    data["generatedAt"] = str(dt.date.today())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"  → {OUT.relative_to(ROOT)} を更新しました")

    # 全滅していたら CI を赤くする（静かに空データを配信しないため）
    return 1 if not fetched else 0


if __name__ == "__main__":
    sys.exit(main())

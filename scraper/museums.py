"""
収集対象の館とその取得方法を1か所にまとめた設定表。
ここが唯一の情報源で、site 側の会場リストもここから生成される。

  id        : 内部ID（変えないこと。exhibitions.json の venue と対応）
  name      : 表示名
  short     : 短縮名
  area/station : 区・最寄り駅（アプリのフィルタ用）
  site      : 館トップ（詳細URLの補完と、取得失敗時のリンク先）
  list_url  : 展覧会一覧ページ
  mode      : "http" = requests で取れる / "js" = Playwright が必要
  link      : 展覧会詳細へのリンクを見分ける正規表現（href に対して検索）
  cat       : {正規表現: 種別} 判定ルール。上から順に評価、どれにも当たらなければ default_cat
  default_cat : 既定の種別
  note      : 運用メモ

mode を "js" にしている館は、requests では中身が空で返るか 403 を返す館。
セレクタではなくページ全体のテキストから会期を拾う方式なので、
サイト改修で即死しにくいかわりに、たまにノイズを拾う。おかしな行が出たら
link の正規表現を絞るのが一番効く。
"""

MUSEUMS = [
    dict(id="tnm", name="東京国立博物館", short="東博", area="台東区", station="上野",
         site="https://www.tnm.jp/",
         list_url="https://www.tnm.jp/modules/r_exhibition/index.php?controller=schedule",
         mode="js", link=r"/modules/r_exhibition/",
         cat={r"特別展": "特別展", r"特集": "特集展示"}, default_cat="企画展",
         note="JS描画。一覧URLが変わりやすいので404が出たらトップから辿り直す"),

    dict(id="nmwa", name="国立西洋美術館", short="西美", area="台東区", station="上野",
         site="https://www.nmwa.go.jp/",
         list_url="https://www.nmwa.go.jp/jp/exhibitions/current.html",
         mode="http", link=r"/jp/exhibitions/20\d\d",
         cat={r"特集展示": "特集展示", r"小企画": "小企画", r"コレクション": "コレクション展"},
         default_cat="企画展"),

    dict(id="tobikan", name="東京都美術館", short="都美", area="台東区", station="上野",
         site="https://www.tobikan.jp/",
         list_url="https://www.tobikan.jp/exhibition/",
         mode="http", link=r"/exhibition/20\d\d",
         cat={r"特別展": "特別展", r"コレクション": "コレクション展"}, default_cat="企画展"),

    dict(id="ueno-mori", name="上野の森美術館", short="上野の森", area="台東区", station="上野",
         site="https://www.ueno-mori.org/",
         list_url="https://www.ueno-mori.org/exhibitions/",
         mode="js", link=r"/exhibitions/", cat={}, default_cat="特別展"),

    dict(id="geidai", name="東京藝術大学大学美術館", short="藝大美術館", area="台東区", station="上野",
         site="https://museum.geidai.ac.jp/",
         list_url="https://museum.geidai.ac.jp/exhibit/",
         mode="http", link=r"/exhibit/", cat={}, default_cat="企画展"),

    dict(id="nact", name="国立新美術館", short="新美", area="港区", station="乃木坂",
         site="https://www.nact.jp/",
         list_url="https://www.nact.jp/exhibition_special/",
         mode="http", link=r"/exhibition_special/20\d\d/",
         cat={r"コレクション": "コレクション展"}, default_cat="企画展"),

    dict(id="mori", name="森美術館", short="森美", area="港区", station="六本木",
         site="https://www.mori.art.museum/jp/",
         list_url="https://www.mori.art.museum/jp/exhibitions/index.html",
         mode="http", link=r"/jp/exhibitions/[a-z0-9]+/",
         cat={r"MAMコレクション": "コレクション展", r"MAM": "小企画"}, default_cat="企画展"),

    dict(id="2121", name="21_21 DESIGN SIGHT", short="21_21", area="港区", station="六本木",
         site="https://www.2121designsight.jp/",
         list_url="https://www.2121designsight.jp/",
         mode="http", link=r"/(program|gallery3)/",
         cat={r"/gallery3/": "小企画"}, default_cat="企画展",
         note="cat の判定は href にも当たるので gallery3 をギャラリー3扱いにできる"),

    dict(id="shiodome", name="パナソニック汐留美術館", short="汐留", area="港区", station="新橋",
         site="https://panasonic.co.jp/ew/museum/",
         list_url="https://panasonic.co.jp/ew/museum/exhibition/",
         mode="js", link=r"/museum/exhibition/", cat={}, default_cat="企画展"),

    dict(id="nezu", name="根津美術館", short="根津", area="港区", station="表参道",
         site="https://www.nezu-muse.or.jp/",
         list_url="https://www.nezu-muse.or.jp/jp/exhibition/index.html",
         mode="js", link=r"/jp/exhibition/",
         cat={r"特別展": "特別展"}, default_cat="企画展"),

    dict(id="teien", name="東京都庭園美術館", short="庭園", area="港区", station="目黒",
         site="https://www.teien-art-museum.ne.jp/",
         list_url="https://www.teien-art-museum.ne.jp/exhibition/",
         mode="http", link=r"/exhibition/", cat={}, default_cat="企画展"),

    dict(id="kemco", name="慶應義塾ミュージアム・コモンズ", short="KeMCo", area="港区", station="三田",
         site="https://kemco.keio.ac.jp/",
         list_url="https://kemco.keio.ac.jp/exhibition/",
         mode="http", link=r"/exhibition/", cat={}, default_cat="企画展"),

    dict(id="momat", name="東京国立近代美術館", short="近美", area="千代田区", station="竹橋",
         site="https://www.momat.go.jp/",
         list_url="https://www.momat.go.jp/exhibitions",
         mode="http", link=r"/exhibitions/[\w-]+$",
         cat={r"所蔵作品展": "コレクション展", r"小企画": "小企画"}, default_cat="企画展"),

    dict(id="mimt", name="三菱一号館美術館", short="一号館", area="千代田区", station="東京",
         site="https://mimt.jp/",
         list_url="https://mimt.jp/ex/",
         mode="js", link=r"/ex/", cat={}, default_cat="企画展",
         note="403。Playwright + 通常UA で取得する"),

    dict(id="tsg", name="東京ステーションギャラリー", short="ステギャラ", area="千代田区", station="東京",
         site="https://www.ejrcf.or.jp/gallery/",
         list_url="https://www.ejrcf.or.jp/gallery/exhibition/",
         mode="js", link=r"/gallery/exhibition/", cat={}, default_cat="企画展"),

    dict(id="artizon", name="アーティゾン美術館", short="アーティゾン", area="中央区", station="京橋",
         site="https://www.artizon.museum/",
         list_url="https://www.artizon.museum/exhibition/",
         mode="js", link=r"/exhibition/",
         cat={r"ジャム・セッション": "企画展", r"コレクション": "コレクション展"}, default_cat="企画展",
         note="リダイレクトループを返すことがある。follow_redirects を切って再試行"),

    dict(id="mot", name="東京都現代美術館", short="MOT", area="江東区", station="清澄白河",
         site="https://www.mot-art-museum.jp/",
         list_url="https://www.mot-art-museum.jp/exhibitions/",
         mode="js", link=r"/exhibitions/",
         cat={r"コレクション": "コレクション展"}, default_cat="企画展",
         note="403。Playwright 必須"),

    dict(id="top", name="東京都写真美術館", short="写美", area="目黒区", station="恵比寿",
         site="https://topmuseum.jp/",
         list_url="https://topmuseum.jp/contents/exhibition/index-3541.html",
         mode="http", link=r"/exhibition/\d+",
         cat={r"TOPコレクション": "コレクション展"}, default_cat="企画展"),

    dict(id="mmat", name="目黒区美術館", short="目黒区美", area="目黒区", station="目黒",
         site="https://mmat.jp/",
         list_url="https://mmat.jp/exhibition/",
         mode="http", link=r"/exhibition/",
         cat={r"コレクション": "コレクション展"}, default_cat="企画展"),

    dict(id="operacity", name="東京オペラシティ アートギャラリー", short="オペラシティ",
         area="新宿区", station="初台",
         site="https://www.operacity.jp/ag/",
         list_url="https://www.operacity.jp/ag/",
         mode="http", link=r"/ag/exh",
         cat={r"収蔵品展": "コレクション展", r"project N": "小企画"}, default_cat="企画展"),

    dict(id="sompo", name="SOMPO美術館", short="SOMPO", area="新宿区", station="新宿",
         site="https://www.sompo-museum.org/",
         list_url="https://www.sompo-museum.org/exhibitions/",
         mode="js", link=r"/exhibitions/", cat={}, default_cat="企画展",
         note="403。Playwright 必須"),

    dict(id="icc", name="NTTインターコミュニケーション・センター [ICC]", short="ICC",
         area="新宿区", station="初台",
         site="https://www.ntticc.or.jp/",
         list_url="https://www.ntticc.or.jp/ja/exhibitions/",
         mode="http", link=r"/exhibitions/", cat={}, default_cat="企画展"),

    dict(id="shoto", name="渋谷区立松濤美術館", short="松濤", area="渋谷区", station="渋谷",
         site="https://shoto-museum.jp/",
         list_url="https://shoto-museum.jp/exhibitions/",
         mode="http", link=r"/exhibitions/", cat={}, default_cat="企画展"),

    dict(id="ota", name="太田記念美術館", short="太田記念", area="渋谷区", station="原宿",
         site="https://www.ukiyoe-ota-muse.jp/",
         list_url="https://www.ukiyoe-ota-muse.jp/exhibition",
         mode="js", link=r"/exhibition", cat={}, default_cat="企画展"),

    dict(id="yamatane", name="山種美術館", short="山種", area="渋谷区", station="恵比寿",
         site="https://www.yamatane-museum.jp/",
         list_url="https://www.yamatane-museum.jp/exh.html",
         mode="js", link=r"/exh", cat={}, default_cat="企画展"),

    dict(id="edohaku", name="東京都江戸東京博物館", short="江戸博", area="墨田区", station="両国",
         site="https://www.edo-tokyo-museum.or.jp/",
         list_url="https://www.edo-tokyo-museum.or.jp/exhibition/",
         mode="js", link=r"/exhibition/",
         cat={r"特別展": "特別展"}, default_cat="企画展"),

    dict(id="yayoi", name="弥生美術館", short="弥生", area="文京区", station="根津",
         site="https://www.yayoi-yumeji-museum.jp/",
         list_url="https://www.yayoi-yumeji-museum.jp/",
         mode="http", link=r"/exhibition", cat={}, default_cat="企画展"),

    dict(id="suntory", name="サントリー美術館", short="サントリー", area="港区", station="六本木",
         site="https://www.suntory.co.jp/sma/",
         list_url="https://www.suntory.co.jp/sma/exhibition/",
         mode="js", link=r"/sma/exhibition/", cat={}, default_cat="企画展",
         note="JS描画。requests ではメタ情報しか返らない"),
]

BY_ID = {m["id"]: m for m in MUSEUMS}

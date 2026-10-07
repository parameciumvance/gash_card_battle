## Context

- 名稱來源:`<title>` 寫死在 `index.html`;頂欄 `#title` 與首頁 `#landing-title` 取自 i18n 的 `app.title`(四種語言目前都是日文原名)。`tools/build_zh_cn.py` 把 `app.title` 列在 `SKIP_KEYS`,不做繁簡轉換。
- 目前沒有任何網頁圖示;瀏覽器會請求 `/favicon.ico` 而得到 404。
- 五圓紋已有 `frontend/emblem.svg`(背景紋路用,低不透明度)。

## Decisions

### D1:名稱各語言相同

`app.title` 四種語言都是「Gash Card Battle Online」,不翻譯:它是專有名稱。`build_zh_cn.py` 繼續跳過 `app.title`(理由從「日文作品名」改為「專有名稱,各語言相同」),測試改為檢查四種語言都等於這個名稱、`<title>` 也相同。

### D2:favicon 為 SVG 單檔

- `frontend/favicon.svg`:正方形 viewBox,魔本紅(`#6e1d1d`)圓角方塊(圓角約邊長 20%),金色(`#ffd166`)五圓紋,紋路約佔 80%。
- 16px 下五個圓會糊在一起,所以線寬比背景紋路粗很多(以 16px 可辨識為準)。
- 以 `<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">` 引用,沿用 `/static` 的路由與 `no-cache` 規則。
- 不另做 PNG / ICO:目前主流瀏覽器都支援 SVG favicon;要支援舊版 Safari 或 iOS 主畫面圖示(`apple-touch-icon` 需要 PNG)時再補。
- 不直接改 `emblem.svg`:背景紋路與圖示的顏色、線寬、底色都不同,各自一檔。

### D3:標題字

- 依使用者從參考稿選定的 D 款修改:徽章由圓形改為與網頁圖示相同的圓角方塊(直接用 `favicon.svg`,兩者永遠一致);右側 GASH(魔本紅、粗)/ CARD BATTLE / ONLINE(琥珀色),ONLINE 在文字欄中置中。
- 結構寫在 `index.html`(首頁 `.wordmark.large`、頂欄 `.wordmark.small`),尺寸以 CSS 變數切換;頂欄排成一行,窄螢幕首頁縮小。名稱各語言相同,所以不由 i18n 產生,`app.title` 只設為 `aria-label`,螢幕閱讀器讀到完整名稱。
- 字距在字尾多出的空白:CARD BATTLE 以負右邊距抵銷,ONLINE 以等量左內距平衡,字形才在欄中真正置中。
- 字型 Oswald(SIL OFL 1.1):以 Google Fonts 的 `text=` 只取標題用到的字母,子集約 2.5KB,放在 `frontend/fonts/` 自架並附授權檔。不從 Google 即時載入:不向第三方送出玩家的請求,也不受外部服務影響。標題文字之外的字母不在子集內;改標題字的字母時要重新取子集。

## Risks / Trade-offs

- [不支援 SVG favicon 的瀏覽器顯示預設圖示] → 影響小,需要時再補 PNG。
- [玩家已加入書籤的舊名稱] → 書籤名稱由瀏覽器保存,不受影響。
- [字型載入前] → `font-display: swap`,先以系統無襯線字顯示再替換,不會空白。

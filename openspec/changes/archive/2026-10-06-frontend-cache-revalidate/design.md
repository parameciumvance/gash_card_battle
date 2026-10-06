## Decisions

### D1:用 `no-cache`,不用版本號網址

- 另一種做法是在 `index.html` 引用的檔案加上版本號(`app.js?v=…`),每次部署時更換。這需要建置步驟或伺服器端改寫 HTML,而且 `app.js` 在執行時動態載入的 `i18n/*.json`、`data/*.json`、規則頁也都要帶版本號。
- `no-cache` 加上既有的 `ETag`,一個 middleware 就能涵蓋所有前端檔案。代價是每次載入多幾個 304 的往返;檔案少、都很小,可以接受。

### D2:範圍

- 套用:路徑為 `/`,或以 `/static/`、`/data/` 開頭,且不是 `/static/assets/`。
- 不套用:
  - `/static/assets/`:卡圖內容固定,玩家另外安裝,維持瀏覽器自行快取。
  - `/api/`:動態回應,本來就不會被瀏覽器推估快取。
- 回應若已有 `Cache-Control` 不覆寫。

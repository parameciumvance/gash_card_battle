## ADDED Requirements

### Requirement: 前端資源每次確認更新
伺服器回應前端資源(`/`,以及 `/static/`、`/data/` 之下、卡圖 `/static/assets/` 以外的檔案)時 SHALL 帶 `Cache-Control: no-cache`,讓瀏覽器每次使用前向伺服器確認;檔案未變時 SHALL 以 304 回應帶相同 `ETag` 的條件請求。卡圖(`/static/assets/`)MUST NOT 套用此標頭。部署新版後,瀏覽器 MUST NOT 混用新舊版本的前端檔案。

#### Scenario: 前端檔案每次確認
- **WHEN** 瀏覽器請求 `/static/app.js`
- **THEN** 回應帶 `Cache-Control: no-cache` 與 `ETag`

#### Scenario: 未變更時回 304
- **WHEN** 瀏覽器以上次取得的 `ETag` 再次請求 `/static/app.js`,且檔案未變
- **THEN** 伺服器回 304,不傳送內容

#### Scenario: 卡圖不套用
- **WHEN** 瀏覽器請求 `/static/assets/cards/S-001.jpg`
- **THEN** 回應不帶 `Cache-Control: no-cache`

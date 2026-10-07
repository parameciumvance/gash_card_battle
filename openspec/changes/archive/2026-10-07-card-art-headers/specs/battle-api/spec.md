## ADDED Requirements

### Requirement: 卡圖回應標頭
卡圖(`/static/assets/` 之下)的 `.webp` 回應 SHALL 帶 `Content-Type: image/webp`,MUST NOT 因執行環境的 Python 版本或系統 MIME 對照檔而不同。卡圖的成功回應(200,以及條件請求的 304)SHALL 帶 `Cache-Control: public, max-age=604800`;找不到的卡圖(404)MUST NOT 帶此標頭。卡圖仍依「前端資源每次確認更新」不帶 `no-cache`。

#### Scenario: WebP 的 Content-Type
- **WHEN** 系統 MIME 對照表沒有 `.webp`(如 `python:3.12-slim`),瀏覽器請求 `/static/assets/cards/S-001.webp`
- **THEN** 回應帶 `Content-Type: image/webp`

#### Scenario: 卡圖可長期快取
- **WHEN** 瀏覽器請求存在的 `/static/assets/cards/S-001.webp`,或以上次取得的 `ETag` 再次請求
- **THEN** 回應(200 或 304)帶 `Cache-Control: public, max-age=604800`

#### Scenario: 缺圖不長期快取
- **WHEN** 瀏覽器請求不存在的 `/static/assets/cards/ZZ-999.webp`
- **THEN** 回應 404,不帶 `Cache-Control: public, max-age=604800`

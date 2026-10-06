## MODIFIED Requirements

### Requirement: 卡圖資產與備援
卡圖檔 SHALL 為 WebP,檔名 `{卡號}.webp`,尺寸與原圖相同並保留透明通道(卡片圓角)。卡圖下載腳本 SHALL 依 cards.json 中的 Google Drive 連結下載原圖,轉成 WebP 後存至 `frontend/assets/cards/{卡號}.webp`;已存在 `{卡號}.webp` 的卡 SHALL 跳過(續抓),失敗 SHALL 寫入失敗清單並繼續。其他格式的卡圖檔(例如舊的 `{卡號}.jpg`)MUST NOT 被當作已安裝的卡圖。卡圖缺失 MUST NOT 影響遊戲功能(前端以文字卡面呈現)。

#### Scenario: 下載失敗不阻塞
- **WHEN** 某卡的 Drive 連結無法存取
- **THEN** 腳本記錄至失敗清單並繼續,遊戲中該卡以文字卡面顯示

#### Scenario: 下載後存為 WebP
- **WHEN** 腳本下載到某卡的 PNG 原圖(含透明圓角)
- **THEN** 存成 `{卡號}.webp`,內容為 WebP,尺寸與原圖相同,圓角仍為透明

#### Scenario: 續抓只認 WebP
- **WHEN** 某卡已有 `{卡號}.webp`,另一卡只有舊的 `{卡號}.jpg`
- **THEN** 前者跳過不下載,後者重新下載並存成 `{卡號}.webp`

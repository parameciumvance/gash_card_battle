# battle-ui — 邀請連結與卡圖狀態(delta)

## ADDED Requirements

### Requirement: 公開邀請連結
UI SHALL 於啟動時取得 `GET /api/meta`;存在 `tunnel_url` 時,建房後顯示的加入/觀戰連結 SHALL 以該公開網址為基底(取代 `location.origin`),並提供一鍵複製。無通道時 SHALL 維持現行以 `location.origin` 組連結。

#### Scenario: 通道邀請連結
- **WHEN** launcher 帶通道啟動且玩家 A 建立房間
- **THEN** 等待畫面顯示以 `https://*.trycloudflare.com` 為基底的加入連結,B 於外網點擊即可加入

#### Scenario: 無通道時維持現行
- **WHEN** `tunnel_url` 為 null(開發模式或降級)
- **THEN** 加入/觀戰連結以 `location.origin` 組成,與現況相同

### Requirement: 卡圖安裝狀態提示
`assets.installed` 為 false 或 `count` 少於 `expected` 時,UI SHALL 於首頁顯示非阻斷提示:卡圖未安裝/不完整,及建議安裝路徑(`install_dir`);MUST NOT 阻擋任何遊戲流程。缺圖的卡面 SHALL 以卡背圖(`back.jpg`)佔位,不出現破圖,文字卡面與操作照常。

#### Scenario: 未安裝提示
- **WHEN** 卡圖未安裝時開啟首頁
- **THEN** 顯示提示與建議安裝路徑,仍可正常開局遊玩

#### Scenario: 缺圖卡背佔位
- **WHEN** 盤面渲染一張無對應卡圖檔的卡
- **THEN** 卡圖區以卡背圖佔位,卡名與行動按鈕照常顯示可用

#### Scenario: 部分缺圖
- **WHEN** 卡圖包版本較舊,僅新彈卡片缺圖
- **THEN** 僅缺圖卡以卡背佔位,其餘卡圖正常顯示

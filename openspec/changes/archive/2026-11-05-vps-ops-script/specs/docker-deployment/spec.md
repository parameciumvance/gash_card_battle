# Spec Delta

## ADDED Requirements

### Requirement: 維運腳本的連線
專案 SHALL 提供在本機執行的維運腳本,經 ssh 操作 VPS 部署目錄中的 compose 服務,不需要登入 VPS 手動執行指令。ssh 目標 SHALL 預設為 `dev@dev-vps`,可由環境變數 `GASH_VPS` 覆蓋;部署目錄 SHALL 預設為 `/opt/gash-card-battle`。腳本 MUST NOT 在 VPS 上留下暫存檔,MUST NOT 讀取或傳送部署目錄的 `.env`。ssh 連線或遠端指令失敗時,腳本 SHALL 以非 0 結束並顯示遠端的錯誤訊息。

#### Scenario: 以環境變數指定主機
- **WHEN** 設定 `GASH_VPS=ops@other-host` 後執行任一子指令
- **THEN** 腳本連到 `ops@other-host`,而不是 `dev@dev-vps`

#### Scenario: 連不上 VPS
- **WHEN** ssh 目標無法連線時執行任一子指令
- **THEN** 腳本以非 0 結束並顯示 ssh 的錯誤,不顯示成功訊息

### Requirement: 卡圖同步
維運腳本的卡圖同步 SHALL 比對 VPS 卡圖 volume 中已有的 `{卡號}.webp` 與本機 `frontend/assets/cards/` 中的 `.webp`,只上傳 VPS 上沒有的卡;指定卡號重傳時,這些卡 SHALL 覆蓋 VPS 上的檔案。上傳前 SHALL 列出要上傳的卡號與張數,沒有要上傳的卡時 SHALL 說明並結束;上傳後 SHALL 回報 VPS 上的卡圖總數。只存在於 VPS 的卡圖 MUST NOT 被刪除。同步 MUST NOT 重啟任何容器。

#### Scenario: 只補缺的卡
- **WHEN** 本機有 M-001 與 M-054 的卡圖,VPS 只有 M-001,執行卡圖同步
- **THEN** 只上傳 M-054;VPS 上的 M-001 不變,回報的總數多 1

#### Scenario: 重傳換過的圖
- **WHEN** 指定重傳 M-001,VPS 上已有 M-001
- **THEN** VPS 上的 M-001 換成本機的檔案

#### Scenario: 已經同步
- **WHEN** VPS 上已有本機全部的卡圖
- **THEN** 不上傳任何檔案,說明已經同步

### Requirement: 發布公告前的驗證
維運腳本發布公告前 SHALL 在本機驗證公告檔。伺服器會視為沒有公告的情況(依 `battle-api`「維護公告」:不是合法 JSON、缺少或空白的 `id`、`message` 不是語言對應文字的物件、`until` 無法解析或已過)SHALL 擋下並說明原因,MUST NOT 上傳。驗證 MUST 與伺服器讀取公告檔使用同一套規則。通過後 SHALL 列出各語言的訊息與 `until`,並對可能是錯誤的內容提出提醒(見情境),再詢問是否發布;回答否時 MUST NOT 上傳。以參數明確略過詢問時直接發布。

#### Scenario: 擋下已過期的公告
- **WHEN** 公告檔的 `until` 早於現在
- **THEN** 腳本說明 `until` 已過、伺服器不會顯示,不上傳,以非 0 結束

#### Scenario: 擋下格式錯誤
- **WHEN** 公告檔缺少 `message`
- **THEN** 腳本說明缺少 `message`,不上傳,以非 0 結束

#### Scenario: 提醒佔位文字與缺少的語言
- **WHEN** 公告的 `en` 是 `"..."`、`zh-CN` 是 `"123"`、沒有 `ja`
- **THEN** 腳本提醒 `en`、`zh-CN` 像佔位文字、缺少 `ja`(玩家會看到 `zh-TW`),並詢問是否發布;回答否時不上傳

#### Scenario: 提醒與繁中相同的翻譯
- **WHEN** 公告的 `en` 與 `zh-TW` 的文字完全相同
- **THEN** 腳本提醒 `en` 與 `zh-TW` 相同,可能忘了翻譯

#### Scenario: 提醒沒有時區的 until
- **WHEN** 公告的 `until` 是 `2026-12-01T22:30:00`(沒有時區)
- **THEN** 腳本提醒伺服器會把它當作 UTC,並顯示換算後的台灣時間

### Requirement: 發布與撤下公告
驗證通過(或確認仍要發布)後,維運腳本 SHALL 以原子替換的方式更新 VPS 卡圖 volume 中的公告檔,伺服器在任何時刻都 MUST NOT 讀到寫了一半的內容。撤下公告時 SHALL 刪除該檔案;沒有公告時撤下 SHALL 說明並正常結束。發布或撤下後,腳本 SHALL 查詢公開網域的 `GET /api/announcement`,確認回應與預期一致(發布時 `id` 相符,撤下時為 null),不一致時 SHALL 顯示實際回應並以非 0 結束。發布與撤下 MUST NOT 重啟任何容器。

#### Scenario: 發布後確認生效
- **WHEN** 發布 `id` 為 `2026-12-01-maint` 的公告
- **THEN** VPS 上的公告檔換成新內容,`GET /api/announcement` 回傳該 `id`,腳本回報已生效

#### Scenario: 撤下後確認
- **WHEN** 有公告時執行撤下
- **THEN** 公告檔被刪除,`GET /api/announcement` 回傳 null

### Requirement: 正式站狀態查詢
維運腳本 SHALL 提供唯讀的狀態查詢,一次顯示:公開網域 `GET /api/meta` 回報的版本、VPS 上各 compose 服務的狀態(含健康檢查)、卡圖 volume 中的卡圖張數與本機的張數,以及目前的公告(`id`、`until` 與 `zh-TW` 訊息,沒有時說明沒有公告)。狀態查詢 MUST NOT 修改 VPS 上的任何檔案或容器。

#### Scenario: 查詢狀態
- **WHEN** 執行狀態查詢
- **THEN** 顯示線上版本(例如 `v1.3.3`)、`app` / `cloudflared` / `watchtower` 的狀態、VPS 與本機的卡圖張數、目前公告

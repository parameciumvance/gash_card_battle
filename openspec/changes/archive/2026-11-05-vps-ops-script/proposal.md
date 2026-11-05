# Proposal

## Why

開發已從 VPS 移回本機(dev container 經 Tailscale SSH 連 `dev-vps`),VPS 只跑正式站。原本在同一台主機上直接 `docker compose cp` 的補卡圖、發維護公告,現在要跨機器手動執行 `scp` → `ssh` → `docker compose cp` 等多個指令,容易漏步驟(公告要先寫暫存檔再搬移)。公告的內容也沒有任何檢查:VPS 上 10/12 那則公告的 `zh-CN` 是 `"123"`、`en` / `ja` 是 `"..."`,格式合法,伺服器照樣顯示佔位文字;格式錯誤或 `until` 已過時,伺服器默默視為沒有公告,發布的人不會知道。

## What Changes

- 新增維運腳本 `tools/vps.py`,在本機執行,經 ssh 操作 VPS 上的部署目錄:
  - `cards`:比對 VPS 上已有的卡圖與本機 `frontend/assets/cards/`,只上傳缺少的 `.webp`;`--force <卡號>` 重傳指定的卡(換圖)。
  - `announce <檔案>`:先在本機驗證,伺服器會視為沒有公告的情況(格式錯誤、`until` 已過)擋下;缺少語言、像佔位文字、與 `zh-TW` 相同時提醒;通過後原子替換 VPS 上的公告檔,再以公開的 `GET /api/announcement` 確認已生效。
  - `announce --clear`:撤下公告並確認。
  - `status`:唯讀顯示線上版本、容器狀態、卡圖張數與目前公告。
  - ssh 目標預設 `dev@dev-vps`,可用環境變數 `GASH_VPS` 覆蓋;部署目錄預設 `/opt/gash-card-battle`。
- 公告檔的格式驗證從 `src/gash/api/app.py` 抽成伺服器與腳本共用的純函式;伺服器的行為不變。
- README「卡圖」「維護公告」兩節改用腳本,保留手動指令作為備用。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `docker-deployment`:新增「VPS 維運腳本」需求(卡圖同步、公告發布與撤下、狀態查詢)。

`battle-api` 的「維護公告」需求不變(公告檔的格式與伺服器的讀取規則照舊),只是驗證改由共用函式實作。

## Impact

- 新增 `tools/vps.py`、`tests/test_vps_tool.py`。
- `src/gash/api/app.py`:`read_announcement` 改用共用的驗證函式(新模組,例如 `src/gash/announcement.py`)。
- `README.md`「卡圖」「維護公告」。
- `docker-deployment` spec 與 design。
- 依賴:本機需要 `ssh` 且能連到 VPS(目前經 Tailscale SSH,不需要金鑰);不新增 Python 套件。正式站映像檔不含 `tools/`,不受影響。

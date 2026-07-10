# Proposal: standalone-release

## Why

目前只有開發者能啟動系統(需要 Python 環境、repo checkout、uvicorn 指令),而且玩家 B 無法從外網連入玩家 A 的電腦。為了讓非開發者的 A 玩家「點兩下就開好房、把連結貼給 B 就能開打」,需要單機執行檔發行與內建公開通道。

## What Changes

- 新增 **launcher**:單一進入點,啟動伺服器(僅綁 127.0.0.1)→ 啟動 cloudflared Quick Tunnel 取得公開 https 網址 → 自動開瀏覽器;cloudflared 缺席時優雅降級為僅本機/區網模式。
- 新增 **PyInstaller 打包**(onedir)與打包腳本:每版產出單一 zip(程式 + Python runtime + cloudflared),**不含卡圖**,各版本獨立解壓即用。
- **卡圖外部化**:卡圖自安裝包移除,解析順序為 `GASH_ASSETS_DIR` → exe 旁 `assets/` → 使用者資料夾(如 `%LOCALAPPDATA%\gash-card-battle\assets`)→ repo `frontend/assets/`(開發模式);卡圖由專案維護者另行發佈,玩家安裝一次、跨版本共用。
- **缺圖降級**:未安裝卡圖時遊戲完整可玩,缺圖卡面以 `back.jpg` 佔位,介面提示安裝位置。
- 前端顯示**邀請連結**(通道網址 + `?join=` 房號)供 A 複製給 B。
- 路徑解析抽象化:`ROOT = parents[3]` 的 repo 佈局假設改為可在 PyInstaller 凍結環境(`sys._MEIPASS` / exe 旁)下運作。

## Capabilities

### New Capabilities
- `standalone-release`: 單機發行與啟動 — launcher 生命週期(server + tunnel + 瀏覽器)、打包內容物與資源解析順序、缺卡圖時的降級行為。

### Modified Capabilities
- `battle-api`: 卡圖靜態路由改掛外部解析出的資產目錄;新增執行環境中繼資訊(邀請網址、卡圖安裝狀態)供前端取得。
- `battle-ui`: 缺圖卡面以卡背佔位並提示卡圖安裝位置;入口/等待畫面顯示可複製的公開邀請連結。

## Impact

- **程式碼**:新增 `src/gash/launcher.py`(或同等模組)、`src/gash/paths.py`(資源解析);修改 `src/gash/api/app.py`(mount、meta)、`src/gash/engine/cards.py`(DATA_DIR 解析)、`frontend/app.js`(佔位圖、邀請連結)。
- **建置**:新增 PyInstaller spec 與打包腳本(`tools/`);Windows exe 需在 Windows 或 CI windows runner 上建置。
- **依賴**:新增 dev 依賴 `pyinstaller`;執行期依賴 cloudflared 外部二進位(隨包附帶,非 pip)。
- **不變**:引擎規則、房間協定、既有開發模式啟動方式(`uvicorn gash.api.app:app --reload`)照常運作。

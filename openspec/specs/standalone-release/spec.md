# standalone-release Specification

## Purpose
TBD - created by archiving change standalone-release. Update Purpose after archive.
## Requirements
### Requirement: 資源目錄解析
系統 SHALL 以單一模組解析資源目錄,區分「程式資源」(frontend/、data/)與「卡圖資源」。程式資源:PyInstaller 凍結環境下 SHALL 取自打包目錄(`sys._MEIPASS`),否則取 repo 佈局。卡圖資源 SHALL 依序取第一個存在的目錄:`GASH_ASSETS_DIR` 環境變數 → 執行檔旁 `assets/` → 使用者資料夾(Windows `%LOCALAPPDATA%\gash-card-battle\assets`,其他平台 `~/.local/share/gash-card-battle/assets`)→ repo `frontend/assets/`;全部不存在時 SHALL 回報未安裝狀態並以使用者資料夾為建議安裝位置。

#### Scenario: 開發模式不變
- **WHEN** 於 repo 以 `uvicorn gash.api.app:app` 啟動且未設定環境變數
- **THEN** 程式資源與卡圖均取 repo 既有路徑,行為與現況完全相同

#### Scenario: 發行模式找到使用者資料夾卡圖
- **WHEN** 凍結環境下執行檔旁無 `assets/`,而使用者資料夾存在卡圖
- **THEN** 卡圖自使用者資料夾提供,任一版本的執行檔皆共用同一份卡圖

#### Scenario: 環境變數優先
- **WHEN** 設定 `GASH_ASSETS_DIR` 指向自訂目錄
- **THEN** 卡圖一律取自該目錄,忽略其他位置

#### Scenario: 完全未安裝卡圖
- **WHEN** 所有搜尋位置皆不存在
- **THEN** 系統回報未安裝(含建議安裝路徑),伺服器正常啟動且遊戲可完整進行

### Requirement: 啟動器
發行版 SHALL 提供單一進入點(launcher):啟動遊戲伺服器(僅綁定 127.0.0.1,埠號自動避讓)後自動開啟瀏覽器進入首頁;伺服器 SHALL 以單一 worker 運行。launcher 結束時 SHALL 一併終止其啟動的子行程。開發環境 SHALL 可以 `python -m gash.launcher` 執行同一流程。

#### Scenario: 點兩下即玩
- **WHEN** 玩家執行發行版執行檔
- **THEN** 伺服器啟動、瀏覽器自動開啟首頁,可直接建房或本機對戰

#### Scenario: 埠號被占用
- **WHEN** 預設埠號已被其他程式占用
- **THEN** launcher 自動改用可用埠號並以該埠開啟瀏覽器

### Requirement: 公開通道
launcher SHALL 在執行檔旁存在 cloudflared 時,以子行程建立 Quick Tunnel 並解析公開 https 網址(每次嘗試逾時上限 30 秒);Quick Tunnel 申請為免費無 SLA 服務,偶發伺服器端錯誤(如 error 1101)時 SHALL 自動重試(至多 3 次)。取得的網址 SHALL 提供給前端作為邀請連結的基底。cloudflared 不存在或重試用盡,SHALL 降級為僅本機/區網模式:遊戲照常可用,通道網址回報為空。

#### Scenario: 通道建立成功
- **WHEN** cloudflared 存在且成功建立通道
- **THEN** 前端可取得 `https://*.trycloudflare.com` 網址,玩家 B 經該網址加入房間並以 wss 正常對戰

#### Scenario: 無 cloudflared 降級
- **WHEN** 執行檔旁不存在 cloudflared
- **THEN** launcher 正常啟動本機遊戲,通道網址為空,不阻擋任何本機/區網功能

#### Scenario: 申請暫時失敗自動重試
- **WHEN** cloudflared 申請 Quick Tunnel 遇伺服器端錯誤退出(如 error 1101),下一次嘗試成功
- **THEN** launcher 自動重啟 cloudflared 取得網址,玩家無感

#### Scenario: 通道解析逾時
- **WHEN** cloudflared 連續多次(達重試上限)未輸出可解析的公開網址
- **THEN** launcher 放棄通道並降級,終端保留各次原始輸出供除錯

### Requirement: 發行打包
打包 SHALL 產出單一 zip(PyInstaller onedir):含執行檔、Python runtime、前端與資料檔、cloudflared;MUST NOT 含卡圖(`assets/cards/`)。各版本 zip SHALL 獨立解壓即用,不依賴先前版本的檔案(卡圖除外,其為選配外部資源)。zip 命名 SHALL 含 `pyproject.toml` 的版本號。

#### Scenario: 新版本獨立安裝
- **WHEN** 玩家將新版本 zip 解壓至任意新資料夾並執行
- **THEN** 系統完整可用(卡圖已裝於使用者資料夾者自動沿用),無須沿用或覆蓋舊版檔案

#### Scenario: 發行物不含卡圖
- **WHEN** 檢查發行 zip 內容
- **THEN** 不存在任何 `assets/cards/` 卡圖檔


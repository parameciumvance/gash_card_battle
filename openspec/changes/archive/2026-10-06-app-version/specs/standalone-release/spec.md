## MODIFIED Requirements

### Requirement: 發行打包
打包 SHALL 產出單一 zip(PyInstaller onedir):含執行檔、Python runtime、前端與資料檔、cloudflared;MUST NOT 含卡圖(`assets/cards/`)。各版本 zip SHALL 獨立解壓即用,不依賴先前版本的檔案(卡圖除外,其為選配外部資源)。zip 命名 SHALL 含 `pyproject.toml` 的版本號。發行物 SHALL 含打包時 `git describe --tags --always --dirty` 的結果(`data/version.txt`),作為執行時回報的版本號。

#### Scenario: 新版本獨立安裝
- **WHEN** 玩家將新版本 zip 解壓至任意新資料夾並執行
- **THEN** 系統完整可用(卡圖已裝於使用者資料夾者自動沿用),無須沿用或覆蓋舊版檔案

#### Scenario: 發行物不含卡圖
- **WHEN** 檢查發行 zip 內容
- **THEN** 不存在任何 `assets/cards/` 卡圖檔

#### Scenario: 發行物帶版本號
- **WHEN** 在 tag `v0.9.1` 的 commit 上打包,玩家解壓後執行
- **THEN** `GET /api/meta` 的 `version` 為 `v0.9.1`

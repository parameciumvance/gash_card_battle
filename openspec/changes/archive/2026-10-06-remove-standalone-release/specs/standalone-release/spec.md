## REMOVED Requirements

### Requirement: 資源目錄解析
**Reason**: 不再提供單機發行版;PyInstaller 凍結佈局、執行檔旁 `assets/`、使用者資料夾的搜尋只為單機版存在。
**Migration**: 卡圖目錄改由 `battle-api`「卡圖靜態資源外部化」規範:`GASH_ASSETS_DIR` 或 repo `frontend/assets/`。

### Requirement: 啟動器
**Reason**: 不再提供單機發行版。
**Migration**: 開發環境以 `uvicorn gash.api.app:app --reload` 啟動;部署見 `docker-deployment`。

### Requirement: 公開通道
**Reason**: 不再提供單機發行版;VPS 經 `docker-deployment` 的 Cloudflare Tunnel 對外,網址固定。
**Migration**: `/api/meta` 不再回報 `tunnel_url`,邀請連結以 `location.origin` 組成(見 `battle-ui`「公開邀請連結」)。

### Requirement: 發行打包
**Reason**: 不再提供單機發行版。
**Migration**: 版本號只由 `GASH_VERSION`(Docker)或 `git describe`(開發環境)取得;已發出的 zip 不再維護。

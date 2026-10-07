## MODIFIED Requirements

### Requirement: CI 測試與建置分流
CI SHALL 區分「一般提交」與「正式發布」兩種流程:push 或 pull request 到主分支時只執行測試套件,不得觸碰部署環境;僅當推送符合版本號格式(`v*`)的 tag 時,才建置映像檔並推送至容器登錄庫。正式發布時,更新內容(見 `battle-ui`「更新內容」)MUST 已有與該 tag 相同版本號的條目,否則 CI MUST NOT 建置映像檔;建置推送後 SHALL 以該版的繁體中文更新內容建立 GitHub Release。CI MUST NOT 持有任何能連進 VPS 的常駐憑證(SSH 金鑰、VPN 授權等)——容器更新由 VPS 端自行輪詢容器登錄庫觸發,不是 CI 主動推送。

#### Scenario: 一般 push 不影響線上服務
- **WHEN** 開發者 push 一般commit 到主分支
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS、線上服務不受影響

#### Scenario: 打版號 tag 觸發建置
- **WHEN** 開發者推送符合 `v*` 格式的 tag(如 `v0.2.0`),更新內容已有 `v0.2.0` 的條目
- **THEN** CI 建置映像檔並推送至容器登錄庫、標上該版號與 `latest`,並以 `v0.2.0` 的繁中更新內容建立 GitHub Release,流程到此結束,不連線 VPS

#### Scenario: 缺少更新內容時不發布
- **WHEN** 開發者推送 tag `v0.2.1`,但更新內容沒有 `v0.2.1`
- **THEN** CI 失敗並指出缺少的版本,不建置映像檔,線上服務維持原版本

# Spec Delta

## MODIFIED Requirements

### Requirement: CI 測試與建置分流
CI SHALL 區分「一般提交」與「正式發布」兩種流程:push 或 pull request 到主分支或開發分支(`dev`)時只執行測試套件,不得觸碰部署環境;僅當推送符合版本號格式(`v*`)的 tag 時,才建置映像檔並推送至容器登錄庫。正式發布時,更新內容(見 `battle-ui`「更新內容」)MUST 已有與該 tag 相同版本號的條目,否則 CI MUST NOT 建置映像檔;建置推送後 SHALL 以該版的繁體中文更新內容建立 GitHub Release。CI MUST NOT 持有任何能連進 VPS 的常駐憑證(SSH 金鑰、VPN 授權等)——容器更新由 VPS 端自行輪詢容器登錄庫觸發,不是 CI 主動推送。

#### Scenario: 一般 push 不影響線上服務
- **WHEN** 開發者 push 一般commit 到主分支
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS、線上服務不受影響

#### Scenario: 開發分支的 push 執行測試
- **WHEN** 開發者 push commit 到 `dev`
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS

#### Scenario: 打版號 tag 觸發建置
- **WHEN** 開發者推送符合 `v*` 格式的 tag(如 `v0.2.0`),更新內容已有 `v0.2.0` 的條目
- **THEN** CI 建置映像檔並推送至容器登錄庫、標上該版號與 `latest`,並以 `v0.2.0` 的繁中更新內容建立 GitHub Release,流程到此結束,不連線 VPS

#### Scenario: 缺少更新內容時不發布
- **WHEN** 開發者推送 tag `v0.2.1`,但更新內容沒有 `v0.2.1`
- **THEN** CI 失敗並指出缺少的版本,不建置映像檔,線上服務維持原版本

## ADDED Requirements

### Requirement: CI 執行全套測試
CI 的測試套件 SHALL 是全套,包含瀏覽器測試:CI 環境 SHALL 安裝瀏覽器測試所需的 Chromium,瀏覽器測試 MUST NOT 因 CI 缺少瀏覽器而被略過。CI 的 Python 版本 SHALL 與 production 映像檔相同。同一分支有新的推送時,SHALL 取消該分支還在執行的舊測試;測試工作 SHALL 有逾時上限,卡住時以失敗結束。

#### Scenario: 瀏覽器測試在 CI 執行
- **WHEN** CI 對一般 commit 執行測試套件
- **THEN** 瀏覽器測試實際執行;略過的只有測試本身設計為略過的項目(例如被動搭檔不能借用),沒有因缺少 Chromium 而略過的項目

#### Scenario: 連續推送
- **WHEN** 開發者連續推送兩次到 `dev`,第一次的測試還在執行
- **THEN** 第一次的測試被取消,只有第二次的測試跑完

### Requirement: 發布前的測試關卡
推送版本號 tag 時,CI SHALL 先對該 tag 指向的 commit 執行全套測試,通過後才建置映像檔;測試失敗時 MUST NOT 建置映像檔、MUST NOT 建立 GitHub Release,線上服務維持原版本。

#### Scenario: 測試失敗時不發布
- **WHEN** 開發者推送 tag `v0.2.2`,更新內容已有 `v0.2.2`,但該 commit 有測試失敗
- **THEN** CI 在測試階段失敗,不建置映像檔、不建立 Release,watchtower 不會拉到新版

### Requirement: CI 失敗的診斷資料
瀏覽器測試失敗時,SHALL 保存失敗當下各頁面的截圖,CI SHALL 將截圖上傳為該次執行的 artifact,讓開發者不必重現就能看到失敗時的畫面。測試全部通過時 MUST NOT 上傳。

#### Scenario: 瀏覽器測試失敗
- **WHEN** CI 中某個瀏覽器測試失敗
- **THEN** 該次執行的 artifact 有那個測試失敗當下的頁面截圖,檔名可對應到測試名稱

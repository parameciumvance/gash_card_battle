## Why

每次更新(例如加入音效、手機排版修正)玩家都不會知道;GitHub Release 只有一種語言,玩家也不會去看。需要一份給玩家看、四種語言的更新內容,在網頁上主動告知,同時作為 GitHub Release 的內容。

## What Changes

- 新增各語言的更新內容資料(繁中為主要來源,簡中由工具產生,英文與日文另寫),放在 repo 中隨版本發布。每一版有版本號、日期、可選的標題與條目;條目分新功能 / 修正 / 調整三類。
- 補寫 v0.9.3([調整] 圖片顯示速度優化)與 v0.9.2(標題「公開上線」,無條目)。
- 首頁:最新一版尚未按過「確認」時,跳出該版的介紹;按「確認」後記在瀏覽器,不再跳出,直到有更新的版本。版本號旁新增「更新內容」入口,可隨時查看全部歷史。
- 發布流程:推送版本 tag 時,若更新內容沒有該版本的條目,CI 不建置映像檔;建置後以該版的繁中內容建立 GitHub Release。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「更新內容」(首頁跳出最新一版介紹、隨時查看全部歷史、各語言資料一致)。
- `docker-deployment`:「CI 測試與建置分流」加入發布前的更新內容檢查與建立 GitHub Release。

## Impact

- 前端:`frontend/i18n/releases.<lang>.json`(四種語言)、`app.js`、`index.html`、`style.css`、各語言 i18n 字典(入口、面板、條目分類標籤)。
- 工具:`tools/build_zh_cn.py` 多轉換一個檔案;新增讀取更新內容的發布工具(檢查 tag 的條目、輸出 GitHub Release 內容)。
- CI:`.github/workflows/deploy.yml`(檢查條目、建立 GitHub Release,需要 `contents: write` 權限)。
- 發布流程:打 tag 前必須先 commit 該版的更新內容;README 的發布說明要更新。
- 伺服器 API 與引擎不變。

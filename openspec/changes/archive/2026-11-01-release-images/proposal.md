# Proposal

## Why

v1.3.0 的更新公告想放第 3 賽季新增產品的圖。更新內容目前只有文字條目。

## What Changes

- 更新內容的每一版可加選填的 `images`(`src` 前端靜態檔路徑、`alt` 依語言的說明),在標題下方、條目之前以一列縮圖顯示,下方寫說明;載入失敗只留說明。
- v1.3.0 附第 3 賽季新增的 7 個產品圖(與規則頁「賽季」表第 3 賽季的產品相同,依卡池篩選的產品順序;Ex 卡、特典卡等虛擬產品除外):LEVEL:3 金色的超咒文、賈修・貝爾與夥伴們、傑昂與最兇惡的魔物們、LIMITED EDITION Ⅰ、SPECIAL BOX、魔書卡本 第二彈、魔書擴充片 LEVEL:2;說明用各語言的產品名稱。
- 四語一致性檢查加入圖片檔(說明可不同),並檢查圖片檔存在。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「更新內容的圖片」。

## Impact

- `frontend/app.js`(`releaseBlock`)、`frontend/style.css`、`frontend/i18n/releases.*.json`、`tests/test_i18n_languages.py`、`tests/test_release_notes_ui.py`。

## Why

網站名稱沿用原作卡牌遊戲的日文名稱《金色のガッシュベル!! THE CARD BATTLE》,容易被誤認為官方商品,也不利各語言玩家辨識;瀏覽器分頁也沒有圖示。正名為 Gash Card Battle Online,並以魔本的五圓紋作為網頁圖示。

## What Changes

- 網站名稱改為「Gash Card Battle Online」,各語言相同:瀏覽器分頁標題、頂欄、首頁標題。
- 新增網頁圖示(favicon):魔本紅底、金色五圓紋的圓角方塊(標題字參考稿中的「1 金紋紅底」),SVG 單檔。
- 首頁與頂欄的標題改為標題字(參考稿 D 款修改):左邊是與網頁圖示相同的五圓紋圓角方塊徽章,右邊為 GASH / CARD BATTLE / ONLINE 三行(ONLINE 置中);頂欄排成一行。字型為 Oswald,子集自架。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「網站名稱與圖示」。

## Impact

- 前端:`frontend/index.html`(`<title>`、`<link rel="icon">`、標題字)、`style.css`、`app.js`、新增 `frontend/favicon.svg` 與 `frontend/fonts/`(Oswald 子集與 OFL 授權)、四種語言的 `app.title`。
- 工具:`tools/build_zh_cn.py` 的說明(`app.title` 不轉換的理由)。
- 文件:README 標題、capability map 的系統概觀、`card-data/design.md` 中 `app.title` 的說明。
- 伺服器 API 與引擎不變。

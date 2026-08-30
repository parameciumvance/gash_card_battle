## Why

測試規則(尤其是效果組合、邊界情境)常需要特定的場面(特定卡在特定頁、特定 MP),目前只能靠正常翻頁/戰鬥流程慢慢湊,效率很低。「本機對戰」本來就是雙方全視角、無 fairness 疑慮的模式,適合掛一個簡單的金手指:換魔本頁面的卡、調 MP。順便把這個模式正名為「本機測試模式」,標示它本來就不是給正式對局用的。

## What Changes

- 首頁入口文案「本機對戰」改為「本機測試模式」(`ui.landing.local` 及對應說明文字、README)。
- 新增金手指端點,**僅 `room.mode == "local"` 開放**(`online` 房一律 403):
  - `GET /api/rooms/{code}/debug-state`:回傳雙方的 `book`(32 頁卡號)與 `mp`。
  - `POST /api/rooms/{code}/debug-state`:收編輯後的 `book`/`mp`,驗證卡號存在於卡片資料庫、`book` 長度為 32,通過後取代對應欄位;成功後 emit 一個 `cheat_applied` 標記事件並沿用既有 `_broadcast` 推送完整快照給所有連線(雙方玩家與觀戰者)。
- 前端在 `mode==local` 的對局畫面新增一個金手指面板:雙方各一個文字框(顯示/編輯 `book` 陣列 JSON)+ MP 數字輸入框,「套用」送出、「重新整理」重新取得目前狀態。
- **BREAKING**:無(純新增端點與 UI;既有線上/本機對局流程不變)。

## Capabilities

### New Capabilities

- `local-test-mode`:本機測試模式的金手指端點(僅限 book/mp)與變更的留痕、同步機制。

### Modified Capabilities

- `battle-ui`:「首頁入口」需求文案由「本機對戰」改為「本機測試模式」;新增「金手指面板」需求(僅本機模式呈現的 book/mp 編輯 UI)。

## Impact

- `src/gash/api/app.py`:新增 `GET`/`POST /api/rooms/{code}/debug-state`
- `frontend/app.js`、`frontend/i18n/zh-TW.json`:金手指面板 UI、文案改名
- `README.md`:「本機對戰」描述文字同步改名
- 不影響:`online` 房間的任何行為、既有指令提交管線(`submit()`)、引擎規則本身、`slots`/`modifiers`/`standby` 等其餘狀態欄位

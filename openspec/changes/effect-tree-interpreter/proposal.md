## Why

卡片效果目前是「一卡一組函式 + 字串 key」:例如 E-001 拆成 `e001` / `e001_pick` / `e001_fire`,靠 `CHOICE_RESOLVERS` 與 `Standby.data["callback"]` 的字串串接,函式名與 key 都含卡號,邏輯與註冊混在同一個檔案(spells/mamodo/partners/events 合計約 1,500 行)。這使得:

- 效果邏輯無法重用(例如「選目標 → 待命 → 加魔力」在多張卡各寫一遍)。
- pending 的 `kind` 字串同時被引擎、前端 i18n(`choice.title.e009_pick` 等 32 條)、測試使用,改名牽動三處。
- 待辦中的 history / 重播需要 state 是純資料,而現在的續體藏在函式與字串 key 的約定裡。

現在改的理由:卡池已到 135 張、行為有 248 個測試保護,是重構風險最低的時點;晚做只會讓一卡一函式繼續增加。

## What Changes

- 新增**效果樹**:效果以不可變(frozen dataclass)節點組合,例如 `Choose(target=OwnMamodo(), then=Standby(at=NextStartPhase(), then=AddPower(amount=3000, duration=DUR_TURN)))`,節點命名以語意為主,不含卡號。
- 新增**直譯器**:`run(node, ctx)` 逐層解決節點;遇到停點(等玩家選擇、擲幣確認、待命)時,把 `(source, path, ctx)` 存入 `PendingChoice` / `Standby`,不存閉包;引擎在玩家回應或待命觸發時呼叫 `resume(...)` 從該節點繼續。
- 註冊層新增以效果樹註冊的方式(如 `reg.event("E-001", when=..., effect=<樹>)`),註冊時自動注入 `source` 卡號;註冊檔逐卡一行、依卡號排序。
- **新舊並存**:既有 `@reg.xxx` 裝飾器與 `CHOICE_RESOLVERS` 字串 key 維持可用,逐卡遷移,每遷移一批都以既有測試驗證。
- `Choose` 節點依選項規格自動產生驗證(驗證失敗保留 pending、單一選項自動解決),取代各卡手寫的 `*_pick` 驗證。
- 遷移範圍:本 change 先完成直譯器骨架、E-001、以及擲幣類卡片;其餘卡片遷移與前端 `choice.title.*` 改為依節點種類,列為後續 change。

## Capabilities

### New Capabilities
- `effect-tree`: 效果樹節點、直譯器、續體(source/path/ctx)存取與 resume 的行為契約,以及以效果樹註冊卡片的方式。

### Modified Capabilities
<!-- 無。遷移為內部重構,遊戲可觀察行為(card-effects 既有需求)不變,由既有測試作為回歸保證。 -->

## Impact

- 程式:`src/gash/engine/effects/`(新增效果樹/直譯器模組、`registry.py` 新增註冊入口、`primitives.py` 擴充節點所需積木)、`src/gash/engine/engine.py`(pending 與開始階段待命的 resume 入口)、`src/gash/engine/state.py`(`PendingChoice` / `Standby` 增加續體欄位)。
- 已遷移的卡:E-001 及擲幣類卡片的 `spells.py` / `events.py` 對應段落被註冊行取代。
- 前端 / i18n / API 格式:本 change 不改動;已遷移卡片的 pending `kind` 需維持前端既有 i18n key 可對應,直到後續 change 統一改名。
- 測試:既有 248 個測試需全數通過;新增直譯器與各節點的單元測試。
- 無新增外部依賴。

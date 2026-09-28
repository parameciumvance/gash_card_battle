## MODIFIED Requirements

### Requirement: 停點續體為純資料
效果解決過程中遇到停點(等待玩家選擇、擲幣確認、待命)時,系統 SHALL 只在遊戲狀態中儲存純資料的續體(可識別效果、停點位置與 `ctx`),MUST NOT 儲存閉包或函式物件。續體 MUST 可 JSON 序列化。

#### Scenario: 停點時狀態可序列化
- **WHEN** 效果因 `Choose` 進入 pending
- **THEN** pending 中的續體只含字串、數字、布林、null、list 與 dict,可直接 `json.dumps`

#### Scenario: 從停點之後繼續
- **WHEN** 玩家回應 `Choose` 的 pending
- **THEN** 直譯器依續體找回該節點,把選擇值寫入 `ctx` 後,只解決該節點之後的節點,不重跑之前的節點

#### Scenario: 續體經序列化往返後仍可恢復
- **WHEN** 停點的續體經 `json.dumps` 再 `json.loads` 後交給 `resume`
- **THEN** 效果照常繼續,結果與未經序列化相同

### Requirement: 決策回應依建立來源分派
系統 SHALL 只把由效果樹節點建立的決策(`Choose`、`CoinWithPaidReflip` 的詢問)的玩家回應交回效果樹,由建立該決策的節點續行。擲幣確認鏈的內部決策(`coin_confirm`、`opp_coin_redo`)MUST 依決策種類交給原本的 M-012 / M-019 處理,確認鏈全部結束後才回到效果樹;擲幣確認結束與待命觸發時的續行 MUST NOT 被當成玩家對樹內決策的回應。任何節點的 `prompt` MUST NOT 與引擎保留的決策種類或既有 resolver key 相同,註冊時檢查並拒絕。

#### Scenario: 確認 pending 不被誤送進樹
- **WHEN** 效果樹的 `Coin` 造成 `coin_confirm` pending,玩家回應保留(`None`)或重擲第幾枚(整數)
- **THEN** 由既有 M-012 resolver 處理(含能力消耗與重擲事件),確認鏈結束後才回到樹

#### Scenario: M-019 串接 M-012
- **WHEN** 對手場上有可用 M-019、玩家場上有可用 M-012,效果樹擲幣
- **THEN** 依序出現 `opp_coin_redo`(決策者為對手)與 `coin_confirm`(決策者為玩家)兩個 pending,各自依原流程解決,最後才進入樹的分支

#### Scenario: 保留 kind 被拒絕
- **WHEN** 註冊一個 `Choose(prompt="coin_confirm")` 或 `CoinWithPaidReflip(prompt="coin_confirm")`
- **THEN** 註冊時拋出錯誤

### Requirement: 付費重擲節點在節點內部迴圈
`CoinWithPaidReflip` 節點 SHALL 擲幣並沿用既有確認鏈;結果符合條件時解決其 `then`,不符合且擁有者 MP 不少於費用時,建立詢問 pending(選項為付費重擲 / 停止),玩家選擇重擲時付費後由同一節點重新擲幣,可重複任意次。迴圈 MUST 只發生在該節點內部:節點只在最終完成(結果符合且 `then` 完成、玩家停止、或 MP 不足)時上溯一次,外層節點的副作用恰好執行一次。玩家回應詢問的值 MUST 為 `True` 或 `False`,否則拒絕並保留 pending;選擇重擲但 MP 不足時同樣拒絕;驗證 MUST 先於任何狀態變更。

#### Scenario: 重擲兩次後外層節點只執行一次
- **WHEN** `Sequence(A, CoinWithPaidReflip(cost=2, then=H), B)` 連續擲出反面、反面、正面,玩家兩次都選擇付費重擲
- **THEN** A、H、B 各執行一次,擁有者 MP 減少 4,RNG 呼叫 3 次

#### Scenario: 停止重擲仍續行外層
- **WHEN** 擲出反面,玩家選擇停止
- **THEN** `then` 不執行,外層後續節點照常執行

#### Scenario: MP 不足時不詢問
- **WHEN** 擲出反面且擁有者 MP 少於費用
- **THEN** 不建立詢問 pending,節點直接完成

#### Scenario: 確認鏈先於重擲詢問
- **WHEN** 擁有者場上有可用 M-012,擲出反面
- **THEN** 先出現 `coin_confirm` pending;玩家保留結果後才出現重擲詢問

#### Scenario: 不合法的回應被拒絕
- **WHEN** 玩家對重擲詢問回應 `True` / `False` 以外的值
- **THEN** 指令被拒絕,pending 與 MP 不變

### Requirement: 註冊檔逐卡集中登記
以效果樹註冊的卡片,註冊檔 SHALL 依卡號排序,每張卡的登記集中在一處;同一張卡有多種掛鉤或資料登記(如登場效果加疊放規則、術相容加啟動效果)時,每種一個 `reg.xxx(...)` 呼叫且彼此相鄰。效果邏輯(含使用前置條件與查詢)MUST 位於 `tree.py` 的節點、條件與規格物件及 primitives,不在註冊檔內以 lambda 或具名函式定義。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=has_own_mamodo, effect=…)` 呼叫,`when` 引用 `tree.py` 中的具名條件函式,註冊檔內無 lambda 或 handler 函式定義

#### Scenario: 同一張卡的多個登記相鄰
- **WHEN** 檢視 M-027(疊放規則 + 無術攻擊規格)的登記
- **THEN** 為相鄰的 `reg.stack_on("M-027", …)` 與 `reg.mamodo_attack("M-027", …)` 兩個呼叫,前後都是卡號不同的卡

## RENAMED Requirements

- FROM: `### Requirement: pending 依專屬標記分派`
- TO: `### Requirement: 決策回應依建立來源分派`

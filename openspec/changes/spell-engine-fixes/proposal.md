## Why

審查 `cards_ja.csv` 權威來源與引擎實作的落差,發現一系列真正影響遊戲判定的問題,不是資料層面的翻譯精確度問題:

1. **「非バトル」術卡從未有正確的使用管道**:S-026(第一彈)、S-041/S-043/S-048/S-057(Level 2)這 5 張的 `effect_icon` 是「非バトル」(自分のターン直接使用,不經過戰鬥宣告),但目前都借用 `declare_attack` 流程觸發,其中 S-041/S-043/S-048/S-057 還額外寫死 `attack_undefendable = True`——JA 原文完全沒有「不可防禦」規則,這個標記唯一的實際作用是擋掉對手的 `declare_defense` 指令,是為了讓「借用戰鬥流程」這件事勉強運作下去的權宜補丁。真正該做的是使用引擎裡已經預留、目前只服務 EVENT 卡的 `use_book_card` 擴充點(engine.py:439-441 明確留了註解「第一彈無『非戰鬥』術;保留擴充點」)。
2. **S-036 的傷害結算繞過正規管線**:`injure_or_discard`(engine.py:111-125)是專為 S-036 寫的旁路函式,只檢查 M-031 查詢型免疫與全免疫,完全沒有走 `_start_damage`/`_process_damage` 正規管線——庇護選擇、P-006 待命無效 1 次傷害、M-013/M-015 戰鬥中免疫 modifier 這三種防護手段對 S-036 全部失效。JA 原文用詞是標準的「ダメージをあたえる」,跟其他所有走正規管線的效果用語一致,沒有特殊語意。
3. **3 張卡完全沒有效果實作**:S-042(比雷茲,魔力門檻+2 傷害)、S-045(岡茲加隆,擲 2 幣 2 正→不可防禦)、S-046(艾傑斯加隆,擲 1 幣正→不可防禦)在 `effects/spells.py` 裡完全沒有任何 handler 註冊,目前只有基礎 `damage` 生效,額外規則完全沒有實作。

這些問題部分是本次審查(對照 `cards_ja.csv` 與 `effects/*.py`)才第一次系統性核對出來,部分(S-036 的措辭問題)在 `retranslate-zh-from-ja` 已被觸及但當時範圍限定在翻譯文字、未回頭查引擎程式碼。

## What Changes

- 依賴 `cards-json-schema-fixes` 新增的 `effect_icon` 欄位,補完 `_use_book_card` 對 `type=="spell"` 的處理:新增一個獨立的 handler 註冊表(非戰鬥術),檢查 `effect_icon=="nonbattle"`、依 `ad` 判斷回合時機(A=自分のターン、D=相手のターン,同 EVENT 卡邏輯)、檢查對應魔物是否在場(指示術/コマンド除外)、支付 MP、呼叫 handler。
- S-026/S-041/S-043/S-048/S-057 的 handler 改註冊到新的非戰鬥術通道,移除 `declare_attack`/`on_declare` 觸發路徑,移除 S-041/S-043/S-048/S-057 誤植的 `attack_undefendable = True`。各卡原有效果邏輯本體(擲幣判斷、羅布諾斯轉換、疊裝甲、待命設定)不變,只換觸發入口。
- `S-036` 的 `_s036_on_win` 改為組一份 `items` 清單(魔本 1 筆 + 對手每隻魔物各 1 筆)呼叫 `_start_damage`,取代 `injure_or_discard`;`injure_or_discard` 函式本身刪除(改動後全專案不再有任何呼叫點)。
- 新增 S-042/S-045/S-046 的 handler:
  - S-042:`SpellRider` 新增 `damage_bonus` 可選欄位(callable,依 `battle.data["attack_total"]` 計算加成),`_attack_damage_amount` 消費它;S-042 註冊 `damage_bonus=lambda game, battle: 2 if battle.data.get("attack_total", 0) >= 8000 else 0`。
  - S-045:`on_declare` 擲 2 幣,2 正 → 設定 `battle.attack_undefendable = True`(這裡是走真正戰鬥流程,設置是正確用法,不同於 S-041 系列的誤用)。
  - S-046:`on_declare` 擲 1 幣,正 → 同上設定。

## Capabilities

### Modified Capabilities

- `game-engine`:「使用場上與魔本中卡片的效果」需求已經要求「非戰鬥術使用後至下回合前不可再用」,但沒有描述「依 `ad` 決定可使用的回合時機(自分/相手のターン)」這個行為細節——補上對應 Scenario。「庇護」需求已經要求「魔本或魔物所受傷害 SHALL 可由自己場上其他魔物庇護」——這是既有規則,S-036 目前違反它,修正後不需要改規格文字,僅需確認既有 Scenario 涵蓋此案例。
- `card-effects`:「第二彈 67 種卡全數可用」需求擴大範圍為 68 種(含 S-042),新增 Scenario 涵蓋 S-042/S-045/S-046 的驗收標準。

## Impact

- `src/gash/engine/engine.py`:`_use_book_card` 補完 SPELL 分支、新增非戰鬥術 handler 註冊表與 `_attack_damage_amount` 的 `damage_bonus` 消費、刪除 `injure_or_discard`
- `src/gash/engine/effects/spells.py`:S-026/S-041/S-043/S-048/S-057 改註冊點,S-036 改用 `_start_damage`,新增 S-042/S-045/S-046 handler
- `src/gash/engine/effects/registry.py`:`SpellRider` 新增 `damage_bonus` 欄位,新增非戰鬥術 handler 註冊表
- `frontend/app.js`:`renderPendingDialog` 補上 `damage_order` 選項的可讀標籤(魔本/對應卡片),取代原本只顯示索引數字的陽春 fallback——此路徑在這次變更前從未被實際對局觸發過,是隨 S-036 修正一併發現並修好的既有前端缺口
- 依賴:`cards-json-schema-fixes` 的 `effect_icon` 欄位(必須先完成該變更或至少先有此欄位資料)
- 測試:需要新增/調整涵蓋這 8 張卡(S-026/036/041/042/043/045/046/048/057,共 9 張)的測試案例

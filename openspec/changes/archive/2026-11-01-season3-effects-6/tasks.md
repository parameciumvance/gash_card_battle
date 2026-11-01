## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_6.py`:M-058 依效果文的行為測試(《ポクポクポク》裝上對手捨て札的搭檔、由使用者選、不需對應魔物、觸發登場效果;已有搭檔 / 對手捨て札沒有搭檔 / MP 不足 / 戰鬥中被拒絕;每回合 1 次;借來的搭檔的效果由使用者使用;以代價棄掉、被效果棄掉、隨魔物送墓、回合結束時棄掉都進對手的捨て札並算對手本回合入墓;ウマゴン的戰術與 M-058 使用的指令戰術被拒絕、其他魔物使用的指令戰術可用;「魔物の効果を使えない」時仍拒絕ウマゴン的戰術);執行並確認修改前失敗

## 2. 引擎

- [x] 2.1 `MamodoSlot.partner_owner`;搭檔棄掉集中到依持有者入墓的函式,各路徑改用(D1)
- [x] 2.2 M-058 的戰術限制(D2)
- [x] 2.3 逐張檢查既有搭檔效果有沒有以「搭檔的對應魔物」判定的地方(D4):名指魔物的效果都以名稱判定(如 `OwnAttackBy("ブラゴ")`)、「這隻魔物」以 `self_slot`(即 M-058);只有從魔書換搭檔(tree.py `excluding_self`)檢查對應魔物,屬一般裝備規則,不需修改

## 3. 卡片登記

- [x] 3.1 M-058 登記於 `effects/cards/mamodo.py`
- [x] 3.2 `data/pending_cards.json` 移除 M-058;`tests/test_season3_cards.py` 的開放張數更新;尚未開放卡的範例測試(`test_room_with_ex_card_rejected` 目前用 M-058)改用測試替身

## 4. 前端與 NPC

- [x] 4.1 state 送出 `partner_owner`;借來的搭檔顯示「借用」小標記,四語 i18n;離場的棄牌演出飛向持有者的棄牌區(card_discarded 的 owner),自棄牌區上場的飛卡自該棄牌區飛出(E-011 / E-022 / M-058);瀏覽器測試
- [x] 4.2 NPC 自我對戰牌組含 M-058 不卡住(slow 自我對戰測試)

## 5. 驗證

- [x] 5.1 快速測試組(1484 passed)、相關瀏覽器測試與新增的 slow 測試通過(`test_season3_effects_6.py`、`test_level3_ui.py`、`test_choice_ui.py`、`test_choice_locations.py`、`test_effect_usage.py`、`test_pool_filters_ui.py` 共 115 passed;全套留到 push 前);`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 到 `card-effects`、`game-engine`、`battle-ui` 主 spec
- [x] 6.2 `card-effects/design.md`「行為決定與理由」加入 M-058 的解讀(指令戰術的判定與 atwiki 評論的差異、借來的搭檔歸屬);`game-engine/design.md` 記錄搭檔持有者

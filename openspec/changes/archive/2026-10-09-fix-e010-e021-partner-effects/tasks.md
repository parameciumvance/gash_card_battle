## 1. E-021(引擎)

- [x] 1.1 先寫依效果文的測試(`tests/test_cards.py`),確認修改前失敗:只用 MP +2(負傷魔物維持負傷)、先回復(選第二隻負傷魔物)再 MP +2、先 MP +2 再回復、沒有負傷魔物時不詢問只 +2;決策者為使用者、非法選擇被拒絕(`choose.invalid`)且保留 pending;場上不足 2 隻時被拒絕(`event.condition`)。改寫既有的 `test_e021_heals_first_injured_and_gains_2mp`(它驗證的是不符效果文的行為)
- [x] 1.2 實作 E-021 的兩段選擇(design D1),新增決策種類 `pick_effect` 與選項標籤;刪除不再使用的 `HealFirstInjuredMamodo`;1.1 全過,`pytest tests/test_effect_tree.py tests/test_effect_characterization.py` 全過
- [x] 1.3 確認逾時代打對 E-021 的兩段決策都能送出合法預設(`tests/test_timer.py` 或新增測試)

## 2. P-003 / P-004 / P-006(引擎)

- [x] 2.1 先寫測試,確認修改前失敗:沒有以ブラゴ攻擊時 P-003 可使用(入墓)且傷害不變;同一場第二次使用成立但傷害只 +2;P-004 沒有以ゴフレ攻擊時同理;P-006 沒有 M-010 時可使用且傷害照常
- [x] 2.2 `OwnAttackBy`、`NoBattleDamageModifierFrom` 加 `test(game, ctx)`;P-003 / P-004 改為 `When(...)` 包住效果、移除 `condition`;P-006 移除 `condition`(design D5);2.1 與既有 P-003 / P-004 / P-006 測試全過

## 3. E-010 借用(引擎、API、NPC)

- [x] 3.1 先寫測試,確認修改前失敗:對手有 P-002 與 P-019 時只能選 P-002;只有 P-013 / P-019 時 E-010 被拒絕(`event.condition`);借用後對手的搭檔被棄掉仍可用 `use_borrowed_effect`(P-002:MP 轉移);不棄卡、`ability_used` 的 player 為使用者;同回合再用被拒絕(`ability.used`);P-003 在戰鬥外被拒絕(`ability.timing`);搭檔效果失效時被拒絕(`ability.partner_restricted`);MP 不足被拒絕(`ability.mp`);下回合被拒絕(`ability.none`);以 `use_field_ability` 指定對手的 slot 被拒絕(`ability.target`)。改寫既有的 `test_e010_borrow_opponent_partner` 與 `test_borrow_partner_records_opponent_partner`
- [x] 3.2 候選排除被動搭檔、`BorrowPartner` 改以卡號記錄、新指令 `use_borrowed_effect`、移除 `_use_field_ability` 的借用分支、`register_slot_hook` 接受 `slot=None`(design D2);3.1 全過
- [x] 3.3 對 17 張可借用的搭檔逐張測試:在其時機借用並使用不出錯,效果作用在使用者這一方(「自分」為使用者)
- [x] 3.4 `_effects_view` 公開 `used`;`tests/test_api.py` 驗證借用項目帶 `card` 與 `used`(design D3)
- [x] 3.5 NPC 候選改為 `use_borrowed_effect`(design D4);`tests/test_npc.py` 新增 NPC 借用後會使用的情境,`pytest tests/test_npc.py tests/test_npc_room.py` 全過

## 4. 前端

- [x] 4.1 先寫瀏覽器測試(本機模式),確認修改前失敗:E-010 借用 P-002 後行動欄出現「借用效果:〈卡名〉」,點開放大檢視按「使用」,對手 MP 減少、自己 MP 增加、對手的 P-002 仍在場上、按鈕消失;對手的 P-002 先被棄掉時入口仍在且可使用;借用 P-003 在戰鬥外時「使用」停用;E-021 的效果選擇顯示 `pick_effect` 標題與選項文字
- [x] 4.2 `app.js`:行動欄按鈕、`{kind: "borrowed"}` 放大檢視與使用按鈕、`ability_used` 帶 `via` 的記錄文字、E-021 選項標籤;i18n(`ui.borrowed_effect`、`log.ability_used_borrowed`、`choice.title.pick_effect`、選項標籤)加到 `zh-TW` / `en` / `ja`,簡中以 `tools/build_zh_cn.py` 產生;4.1 與 `pytest tests/test_i18n_languages.py tests/test_choice_ui.py` 全過
- [x] 4.3 使用者在瀏覽器實際操作 E-021、E-010(含借用後搭檔離場)、P-003 沒有ブラゴ時使用

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回 `card-effects`、`battle-ui` 主 spec
- [x] 5.2 Reconcile affected capability design and rationale:`card-effects/design.md`「行為決定與理由」加入 design.md 列出的五項決定,機制一節補充借用指令;`battle-ui/design.md` 補充借用效果入口
- [x] 5.3 確認 capability map 是否需要更新
- [x] 5.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔

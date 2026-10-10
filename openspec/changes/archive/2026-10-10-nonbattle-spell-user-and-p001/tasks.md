## 1. 引擎

- [x] 1.1 先寫測試,確認修改前失敗:非戰鬥戰術指定使用魔物時 `book_card_used` 帶該魔物卡號 `mamodo`,未指定時為費用最低的第一隻可用魔物;對手回合使用 P-001 被拒絕(`ability.timing`)、P-001 仍在場上;(借用只在使用 E-010 的那個自己的回合有效,不會在對手回合出現,不另測);P-007 在對手回合使用成立
- [x] 1.2 `_nonbattle_spell_user` 回傳具體使用魔物、`book_card_used` 加 `mamodo`(design D1);P-001 `own_turn=True`(design D4);1.1 全過,`pytest tests/test_cards.py tests/test_level2.py tests/test_spell_user.py tests/test_npc.py` 全過

## 2. 前端

- [x] 2.1 先寫瀏覽器測試,確認修改前失敗:S-026 在兩隻魔物時按「使用」進入場上選擇;只有一隻時直接使用;使用 S-026 的記錄為「以〔魔物名〕使用戰術《ＳＥＴ！》」,事件卡的記錄仍為「使用事件卡」;對手回合 P-001 的放大檢視按鈕停用並顯示「只能在自己的回合使用」
- [x] 2.2 `pickSpellUser` 規則(design D3)、`book_card_used` 記錄文字(design D2)與 i18n(簡中以工具產生);2.1、`pytest tests/test_spell_user_ui.py tests/test_nonbattle_ui.py tests/test_i18n_languages.py` 全過
- [x] 2.3 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui`、`game-engine`、`card-effects` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`card-effects/design.md` 加入 P-001 的行為決定;`battle-ui/design.md` 更新「戰術的使用魔物與搭檔的裝備對象」(非戰鬥規則)與記錄文字
- [x] 3.3 確認 capability map 是否需要更新
- [x] 3.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔

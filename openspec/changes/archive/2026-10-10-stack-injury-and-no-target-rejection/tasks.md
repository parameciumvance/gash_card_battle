## 1. 疊放繼承負傷

- [x] 1.1 先寫測試,確認修改前失敗:負傷的一般ゴフレ放出 M-007 後仍負傷;E-012 自魔書放出疊放型魔物到負傷前身上仍負傷;S-048 把 M-027 疊在負傷的 M-028 上仍負傷;健康的前身疊放後仍健康。找出驗證「疊放恢復健康」的既有測試,依新行為改寫
- [x] 1.2 移除三處 `injured = False`(design D1);1.1 全過,`pytest tests/test_level2.py tests/test_cards.py tests/test_effect_tree.py` 全過

## 2. 選不到對象時不能使用

- [x] 2.1 先寫測試,確認修改前失敗:S-048 魔書沒有 M-027 / 場上沒有 M-028 時被拒絕(`spell.condition`)、MP 不變、本回合仍可使用;S-043 兩種模式都不可行時被拒絕;分裂時場上放不下不列入模式;分裂由玩家依序選 2 張 M-024,未選的留在魔書,決策者為使用者、非法頁被拒絕且保留 pending;場上滿時只列合體(場上最多 3 隻、M-024 最多 2 隻,兩種模式不會同時可行)
- [x] 2.2 `spell_nonbattle(..., when=)` 與引擎檢查、S-048 / S-043 條件與模式、S-043 分裂改為兩次選擇、移除 `PlaceMamodoFromBookUpTo`(design D2、D3);2.1 全過,`pytest tests/test_effect_tree.py tests/test_npc.py` 全過

## 3. 快照與前端

- [x] 3.1 先寫測試,確認修改前失敗:快照翻開的 S-048 / E-021 頁 `condition_ok` 依條件為 true / false,對手視角沒有;瀏覽器中 S-048 不符合條件時「使用」停用並顯示原因
- [x] 3.2 `_player_view` 加 `condition_ok`、前端停用與 i18n(design D4);3.1 與 `pytest tests/test_nonbattle_ui.py tests/test_i18n_languages.py` 全過
- [x] 3.3 翻閱時的決策目標頁可選(使用者回報 S-048 翻到 M-027 的頁無法選):先寫瀏覽器測試確認失敗,`browsedPageEl` 依 `PICK.book` 發光並提供「選擇」(design D5);`pytest tests/test_book_browse_ui.py tests/test_choice_ui.py tests/test_spell_user_ui.py` 全過
- [x] 3.4 使用者在瀏覽器實際操作確認

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `card-effects`、`battle-api`、`battle-ui` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`card-effects/design.md` 加入兩項行為決定,機制一節補充非戰鬥戰術的使用條件;`battle-ui/design.md`「場上魔書翻閱」補充決策目標頁的例外;`battle-api/design.md` 補充 `condition_ok` 為持有者私有
- [x] 4.3 確認 capability map 是否需要更新
- [x] 4.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔

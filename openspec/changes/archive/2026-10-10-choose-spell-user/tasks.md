## 1. 引擎與快照

- [x] 1.1 先寫測試,確認修改前失敗:`use_book_card` 對非戰鬥戰術指定使用者時依該魔物計費(P-005 生效、指定非スギナ的魔物付原價);指定不能使用的魔物被拒絕(`spell.no_mamodo`);指定被 E-024 封鎖的魔物被拒絕(`spell.mamodo_locked`);只有被封鎖的魔物能用時未指定也被拒絕(`spell.mamodo_locked`);快照 `users`:賈修與 M-029 都在場時「ザケル」頁含兩隻、「バオウ・ザケルガ」頁只有賈修,各附依該魔物的費用與 `locked`;對手與觀戰視角沒有 `users`
- [x] 1.2 `_use_book_card` 非戰鬥戰術接受 `slot_uid`、檢查封鎖;`spell_cost` 未指定時排除被封鎖者(design D2);1.1 引擎測試全過,`pytest tests/test_engine.py tests/test_cards.py tests/test_level2.py` 全過
- [x] 1.3 `_player_view` 加 `users`(design D1);1.1 快照測試全過,`pytest tests/test_api.py tests/test_views.py tests/test_npc.py` 全過
- [x] 1.4 先寫測試,確認修改前失敗:兩隻 M-024 時放出 P-015 指定第二隻,裝在第二隻;第一隻已有搭檔時未指定也裝到第二隻;指定已有搭檔的魔物被拒絕(`play.partner_exists`)、指定不對應的魔物被拒絕(`play.no_mamodo`);P-015 待命生效時快照 `any_page_spells` 列出魔書中的ビライツ頁(含 `users`),待命用掉後不再列出;NPC 候選對兩隻 M-024 各產生一個放出 P-015 的指令
- [x] 1.5 `_play_card` 搭檔分支接受 `slot_uid`、取第一隻候選(design D6);`_player_view` 加 `any_page_spells`(design D5);NPC 搭檔放出候選(design D6);1.4 全過,`pytest tests/test_npc.py tests/test_npc_room.py tests/test_level2.py` 全過

## 2. 前端

- [x] 2.1 先寫瀏覽器測試,確認修改前失敗:賈修與 M-029 都在場時對「ザケル」按「攻擊」跳出選擇,列出兩隻與費用,選ゼオン後宣告的使用者為ゼオン(`S.battle_in` 或事件中的攻擊魔物);只有一隻能用時不詢問且送出 `slot_uid`;只有 M-029 在場時「バオウ・ザケルガ」的攻擊按鈕停用;兩隻中一隻被封鎖時直接以另一隻宣告;非戰鬥戰術兩隻可選且費用不同時跳出選擇、費用相同時不詢問
- [x] 2.2 `spellUsers` / `pickSpellUser`、`spellUsable` / `nonbattleSpellUsable` 改用 `users`、移除 `hasSpellMamodo`、`showDialog` 支援停用與費用說明(design D3);2.1 全過,`pytest tests/test_nonbattle_ui.py tests/test_choice_ui.py tests/test_timing_ui.py` 全過
- [x] 2.3 先寫瀏覽器測試,確認修改前失敗:P-015 待命生效時行動欄出現「從魔書使用〈ビライツ〉」,開啟網格後該頁發光,放大檢視按「攻擊」在兩隻 M-024 時跳出選擇並以選到的魔物宣告;兩隻 M-024 時放出 P-015 跳出裝備對象選擇,選第二隻後裝在第二隻;第一隻已有搭檔時直接裝到第二隻。實作 D5、D6 的前端部分後全過
- [x] 2.4 i18n(design D4),簡中以 `tools/build_zh_cn.py` 產生;`pytest tests/test_i18n_languages.py` 全過
- [x] 2.5 先改瀏覽器測試,確認修改前失敗:使用魔物與搭檔裝備對象改為場上選擇(候選在場上發光,點開按「選擇」;行動欄有提示與「取消」,取消後不送出;不可選的魔物點開時「選擇」停用);左右鍵翻到 P-015 可用的頁時該頁發光、放大檢視有「攻擊」
- [x] 2.6 實作場上選擇(design D3)與翻閱時的任意頁入口(design D5),移除對話框的使用魔物選擇;2.5 與 `pytest tests/test_choice_ui.py tests/test_nonbattle_ui.py tests/test_book_browse_ui.py` 全過
- [x] 2.7 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `game-engine`、`battle-api`、`battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`card-effects/design.md` 加入 E-024 封鎖適用非戰鬥戰術的行為決定(`Confirmed`);`battle-ui/design.md` 補充使用魔物選擇、任意頁戰術入口與搭檔裝備對象選擇;`npc-opponent/design.md` 補充搭檔放出候選;`battle-api/design.md` 補充 `users` 屬於持有者私有資料
- [x] 3.3 確認 capability map 是否需要更新
- [x] 3.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔

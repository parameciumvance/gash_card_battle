## 1. M-018 依效果文(引擎)

- [x] 1.1 先寫「依效果文應該如何」的測試(`tests/test_level2.py`),確認修改前失敗:自己回合非戰鬥中使用 M-018 產生 `pages_peeked`(viewer 為使用者、`cards` 為對手翻開的頁),對手頁無防禦術時 MP −1+2、有時只 −1(保留既有參數化測試);對手回合的戰鬥階段取得行動權後使用被拒絕,錯誤碼精確為 `ability.timing`,MP 不變、沒有 `pages_peeked`、不在 `used_abilities`,且回到自己回合仍可使用;自己回合戰鬥中使用被拒絕(`ability.timing`)
- [x] 1.2 `effects/registry.py` 的 `Activated` 新增 `own_turn`;`engine._use_field_ability` 在支付前檢查,非回合玩家拒絕 `ability.timing`(design D2);以 1.1 的測試與 `pytest tests/test_effect_tree.py tests/test_engine.py` 驗證既有效果不受影響
- [x] 1.3 `effects/cards/mamodo.py`:M-018 改為 `Sequence(PeekOpponentOpenPages(), When(...))`,登記 `own_turn=True`(design D1);1.1 的測試全過
- [x] 1.4 `api/views._ability_view` 輸出 `own_turn`;`tests/test_api.py` 驗證快照中 M-018 的 ability 帶 `own_turn: true`、其他卡為 `false`
- [x] 1.5 NPC 不受影響:`pytest tests/test_npc.py tests/test_npc_room.py` 全過(NPC 只送引擎接受的指令)

## 2. 檢視對話框(前端)

- [x] 2.1 先寫瀏覽器測試(新檔 `tests/test_peek_ui.py`,本機測試模式),確認修改前失敗:使用 E-014 後盤面更新、跳出對話框,依頁碼列出對手翻開的兩頁卡片,按「確定」關閉;使用 M-018 後同樣跳出;重新整理(或重新進入同一房間)後不再跳出;注入 viewer 為對方、不含 `cards` 的 `pages_peeked` 不跳出;對話框開著時計時與按鈕狀態照常
- [x] 2.2 `app.js`:`applyPayload` 在 `Anim.apply` 完成後,對即時批次中含 `cards` 的 `pages_peeked` 以 `showInfo("peek", …)` 顯示卡片列(沿用卡片元件,點擊開放大檢視),「確定」關閉(design D3);2.1 的測試全過
- [x] 2.3 `app.js` 場上效果可用性判斷:`own_turn` 且非自己回合時停用使用按鈕並顯示原因;在 2.1 的測試檔加上對手回合點開 M-018 時按鈕停用的情境
- [x] 2.4 i18n:`ui.peek.title`、頁碼標籤等加到 `zh-TW` / `en` / `ja`,簡中以 `tools/build_zh_cn.py` 產生(design D4);`pytest tests/test_i18n_languages.py` 全過
- [x] 2.5 使用者在瀏覽器實際操作 E-014 與 M-018,確認對話框內容與關閉

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `card-effects`、`battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`card-effects/design.md`「行為決定與理由」新增 M-018 三項決定(限自己回合、限非戰鬥中、先檢視再判斷,狀態依 design.md);機制一節補充 `own_turn` 時機檢查;`battle-ui/design.md` 新增檢視對話框(觸發時點、只對即時批次)
- [x] 3.3 確認 capability map 是否需要更新(責任與覆蓋程度若無變化則不改)
- [x] 3.4 `openspec validate --all --strict` 與 `pytest` 全過後歸檔

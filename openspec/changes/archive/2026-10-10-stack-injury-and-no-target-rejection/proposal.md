## Why

- 魔物疊放出場(變身 / 合體)時,引擎把前身的負傷清掉、恢復健康;規則上疊放應繼承前身的狀態,負傷的魔物疊放後仍是負傷(橫放)。
- S-048 在魔書中沒有 M-027(或場上沒有 M-028)時仍可使用,照樣扣 MP 卻什麼都不會發生;需要選擇對象的效果在選不到對象時應該不能使用。S-043 也只看場上的魔物數,不看魔書中是否有要放出的卡。S-043 分裂目前自動依頁序放出,而效果文是「2枚選び」。
- 不符合使用條件的事件卡,畫面上要按下才被拒絕。

## What Changes

- 疊放出場(從翻開的頁放出、E-012 從魔書放出、S-048 從魔書疊放)繼承前身的負傷狀態。修改 `card-effects`「疊放魔物(變身後)」(原本的情境寫明「以健康狀態生效」)。
- 非戰鬥戰術新增使用條件機制:條件不成立時拒絕(`spell.condition`),不付費。
  - S-048:場上有 M-028 且魔書中有 M-027。
  - S-043:合體(場上 2 隻 M-024 且魔書有 M-025)或分裂(場上有 M-025、魔書至少 2 張 M-024、棄掉 M-025 後場上放得下 2 隻)至少一種可行;選擇模式時只列可行的模式。
  - S-043 分裂改為由玩家從魔書中選剛好 2 張 M-024。
- 快照對翻開的事件卡與非戰鬥戰術附 `condition_ok`;前端停用「使用」並顯示原因。
- 場上魔書翻閱時,進行中「從魔書挑頁」決策的目標頁可直接選擇(原本翻閱一律唯讀,S-048 翻到 M-027 的頁無法選)。
- 維持現狀:E-027(雙方各自處理,效果文沒有「選不到就不能用」)、S-039(主效果是傷害)、M-025(「できる」可選)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改「疊放魔物(變身後)」;新增「選不到對象的非戰鬥戰術不能使用」。
- `battle-api`:新增「魔書中卡片的使用條件」。
- `battle-ui`:新增「不符合使用條件的卡停用」;修改「場上魔書翻閱」(決策目標頁可選)。

## Impact

- 引擎:`engine.py`(`_play_card` 疊放、非戰鬥戰術的條件檢查)、`effects/tree.py`(`DeployMamodoFromBook` 疊放、`StackFromBookOnto`、`RobnosTransformMode`、移除 `PlaceMamodoFromBookUpTo`)、`effects/registry.py`(`spell_nonbattle(..., when=)`)、`effects/cards/spells.py`(S-043、S-048)。
- API:`api/views.py`(`condition_ok`)。
- 前端:`frontend/app.js`(停用與原因)、i18n。
- 測試:`tests/test_level2.py` / `tests/test_cards.py` 既有疊放測試(驗證「恢復健康」者依新行為改寫)、新測試、瀏覽器測試。

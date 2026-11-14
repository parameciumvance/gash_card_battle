# Design

## Context

- season4-mamodo-b D4:`name_deploy_blocked` 在 `play_block` 與部分效果放出的選項規格檢查,漏掉從魔書放出指定名稱 / 卡號的規格與強制放出。
- 2026-11-10 盤點所有放出路徑(效果文含「場に出す」「重ねる」「つける」):E-044 走 `play_block`;E-011、E-022、S-090、M-058 走棄牌區搭檔的規格;E-012、E-027、E-034、E-051、Ex-046、M-062、M-083、MJ-003、P-036、S-140 走 `DeployableMamodoInOwnBook` / `AttachablePartnerPagesInOwnBook`,都已檢查。

## Decisions

### D1:補上的選項規格

- `OwnBookPartnerNamed`、`OwnBookCopiesOf`、`CanStackFromBook` 排除 `name_deploy_blocked` 的卡。S-043 的模式(`RobnosTransformMode`)以 `OwnBookCopiesOf` 計數,所以完全體 / 分身體被擋時對應模式不列出。

### D2:強制放出(使用者決定)

- 結束階段場上沒有魔物時,依規則從翻開頁放出魔物;`name_deploy_blocked` 的魔物不算候選,沒有候選就照規則繼續翻頁尋找(翻到底則敗北)。依字面「場に出すことができない」,不分是否為規則動作。

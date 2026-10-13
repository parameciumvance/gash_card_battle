## Why

E-018「フォルゴレのダンス」在直前的回合自己用過減少對手 MP 的效果時,減少量變成 0。目前這時的行動記錄只寫「效果發動(フォルゴレのダンス)」,和正常發動一模一樣,玩家看到對手 MP 沒變,只能看到使用者自己付的費用「MP -2」,會誤以為是 bug(有玩家回報)。

## What Changes

- E-018 的減少量因「直前のターン」條款變成 0 時,引擎發出專用事件 `opp_mp_reduction_restricted`(取代原本帶 `skipped` 的 `effect_applied`)。
- 行動記錄以四種語言寫出原因,例如「{player} 在上一個回合已使用減少對手 MP 的效果,{source} 減少的 MP 為 0」。
- 從 v1.0.0 開分支修正,不含第三彈資料。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:行動記錄新增「減少對手 MP 的效果被限制為 0」的條目。

## Impact

- `src/gash/engine/effects/tree.py`(`ReduceOpponentMpUnlessReducedLastTurn`)
- `frontend/app.js` 的 `logLine`、`frontend/i18n/*.json`
- 測試:`tests/test_effect_characterization.py` 的 E-018 測試、記錄文字

## ADDED Requirements

### Requirement: 減少對手 MP 被限制為 0 的記錄
效果依效果文把減少對手 MP 的量變成 0 時(E-018 在上一個回合自己已使用過減少對手 MP 的效果),引擎 SHALL 發出 `opp_mp_reduction_restricted` 事件(含使用者與來源卡),行動記錄 SHALL 寫出原因與減少量為 0,MUST NOT 只顯示與一般發動相同的「效果發動」。

#### Scenario: 連續回合使用 E-018
- **WHEN** 玩家 1 在對手的回合用 E-018 減少對手 MP 後,於自己的下一回合再使用 E-018
- **THEN** 對手 MP 不變,行動記錄出現「玩家 1 在上一個回合已使用減少對手 MP 的效果,《フォルゴレのダンス》減少的 MP 為 0」(卡名與文字依目前語言)

## MODIFIED Requirements

### Requirement: 決策回應依建立來源分派
系統 SHALL 只把由效果樹節點建立的決策(`Choose`、`CoinWithPaidReflip` 的詢問)的玩家回應交回效果樹,由建立該決策的節點續行。擲硬幣子階段的內部決策(`coin_confirm`:擲幣者的機會;`opp_coin_redo`:擲幣者對手的機會)MUST 依決策種類交給子階段的處理(M-012、M-034、M-019),子階段結束後才回到效果樹;擲幣確認結束與待命觸發時的續行 MUST NOT 被當成玩家對樹內決策的回應。任何節點的 `prompt` MUST NOT 與引擎保留的決策種類或既有 resolver key 相同,註冊時檢查並拒絕。

#### Scenario: 確認 pending 不被誤送進樹
- **WHEN** 效果樹的 `Coin` 造成 `coin_confirm` pending,玩家回應保留(`None`)或重擲第幾枚(整數)
- **THEN** 由既有 M-012 resolver 處理(含能力消耗與重擲事件),確認鏈結束後才回到樹

#### Scenario: M-019 串接 M-012
- **WHEN** 對手場上有可用 M-019、玩家場上有可用 M-012,效果樹擲幣
- **THEN** 依擲硬幣子階段先出現 `coin_confirm`(決策者為玩家),玩家不使用後出現 `opp_coin_redo`(決策者為對手),各自依子階段解決,最後才進入樹的分支

#### Scenario: 保留 kind 被拒絕
- **WHEN** 註冊一個 `Choose(prompt="coin_confirm")` 或 `CoinWithPaidReflip(prompt="coin_confirm")`
- **THEN** 註冊時拋出錯誤

### Requirement: Coin 節點包住重擲確認鏈
`Coin` 節點 SHALL 由指定的擲幣者(`flipper`,預設為效果擁有者,可指定為對手)擲指定數量硬幣並經過擲硬幣子階段(見 `game-engine`「擲硬幣子階段」:擲幣者先以 M-012 / M-034,擲幣者的對手以 M-019 令其重擲 1 枚,雙方輪替),子階段結束後才依結果分支繼續。無論擲幣者是誰,`ctx["player"]` MUST 維持為效果擁有者。`Coin` MUST 僅在第一次執行該節點時消耗 `game.rng` 做初始擲幣;效果樹的 resume 不得再次初始擲幣。玩家在子階段使用的 M-012 / M-019 重擲,每次重擲 1 枚、消耗 1 次 RNG。

#### Scenario: 擲幣結果決定分支
- **WHEN** 防守方宣告 S-025,擲 1 枚硬幣為正面
- **THEN** 攻擊被無效化,事件與遷移前一致

#### Scenario: 確認鏈期間停下
- **WHEN** 玩家場上有可用的 M-012,其效果樹擲幣後進入重擲確認
- **THEN** 進入 pending 等待玩家決定,決定後才繼續解決 `Coin` 之後的節點

#### Scenario: RNG 消耗次數與遷移前相同
- **WHEN** 以會在超額呼叫時失敗的 RNG 重跑各擲幣入口(傷害後、宣告時、非戰鬥)
- **THEN** 遷移前後 RNG 呼叫次數與結果相同;有重擲時,額外消耗僅來自玩家合法的重擲

#### Scenario: 由對手擲幣
- **WHEN** 玩家使用 E-020,由對手擲 1 枚硬幣為正面
- **THEN** `coin_flipped` 事件的擲幣者為對手;使用者 MP +3、對手 MP +3;對手場上的 M-012 由對手決定是否重擲,使用者場上的 M-019 由使用者決定是否令對手重擲

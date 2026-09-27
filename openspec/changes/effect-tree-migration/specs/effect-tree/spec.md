## MODIFIED Requirements

### Requirement: 效果樹與既有註冊方式並存
系統 SHALL 同時支援以效果樹註冊與既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊;同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移為內部重構,遊戲可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 已遷移與未遷移的卡並存
- **WHEN** E-001 以效果樹註冊、E-002 仍以裝飾器註冊,雙方各使用一次
- **THEN** 兩者都正常解決,既有測試全數通過

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

#### Scenario: 逐批遷移過程中整體卡池行為不變
- **WHEN** 效果樹遷移(`effect-tree-migration`)跨多次工作階段逐批進行,任一時間點都同時存在已遷移與未遷移的卡
- **THEN** 每一批遷移前後,`card-effects` spec 涵蓋的全部卡片既有測試(含該批遷移前補上的特徵測試)皆全數通過;遷移未完成不影響尚未遷移的卡正常運作

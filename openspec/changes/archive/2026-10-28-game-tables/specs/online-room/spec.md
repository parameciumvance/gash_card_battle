## MODIFIED Requirements

### Requirement: 加入房間與開局
系統 SHALL 提供加入端點:以房號換取第二位玩家的 token,可附上加入者自己的牌組(缺省 level1;自訂牌組 MUST 通過構築規則驗證,違規回 422 且不佔用玩家位)與**可選暱稱**(清理規則同建房)。雙方到齊即以各自的牌組建立引擎對局並向所有連線廣播開局。已滿的房間 MUST 拒絕再加入為玩家(仍可觀戰);不存在的房號 MUST 回 404。牌桌的房間(見 `game-tables`)MUST NOT 以房號加入,回 409 `room.table_only`;須經牌桌入座。

#### Scenario: 對手加入即開局
- **WHEN** 第二位玩家以房號 POST join
- **THEN** 回傳其 player_token,雙方 WebSocket 均收到開局狀態

#### Scenario: 雙方各用自己的牌組
- **WHEN** 建房者與加入者各附上不同的合法牌組
- **THEN** 開局後兩人的魔書內容互異,各自視角只見自己的翻開頁內容

#### Scenario: 加入者帶暱稱
- **WHEN** 加入者附上暱稱「小美」
- **THEN** 房間記錄玩家 1 的暱稱;雙方畫面皆以該暱稱顯示玩家 1

#### Scenario: 滿房拒絕第三位玩家
- **WHEN** 已有兩位玩家的房間再收到 join
- **THEN** 回應錯誤,房內對局不受影響

#### Scenario: 牌桌的房間不能用房號加入
- **WHEN** 有人以牌桌上等待中房間的房號 POST join
- **THEN** 回應 409 `room.table_only`,牌桌與房間狀態不變

# online-room — 差分:開局攜帶牌組與伺服器裁決

建房/加入請求新增可選 `deck` 欄位;伺服器以既有 validate_deck 做構築合法性的最終裁決;牌組僅存在房間生命週期內。

## MODIFIED Requirements

### Requirement: 建立房間
系統 SHALL 提供建房端點:指定模式(online/local)、計時選項(關/30/60/120 秒)與可選的牌組(缺省為 level1 預組;自訂牌組為 32 個卡號的頁序,本機房可為雙方各指定一副),回傳房號(6 碼英數)、建房者的玩家 token、加入連結與觀戰連結。自訂牌組 MUST 於受理前以構築規則驗證,違規回 422 與對應原因碼。線上房 MUST 於第二位玩家加入後才建立對局並開局;本機房 MUST 立即開局並一次回傳雙方 token。牌組 MUST 只存在於房間生命週期內,伺服器不持久化。

#### Scenario: 建立線上房
- **WHEN** 客戶端 POST 建房(mode=online, timer=60)
- **THEN** 回傳房號、player_token、join_url、spectate_url,且對局尚未開始

#### Scenario: 本機房立即開局
- **WHEN** 客戶端 POST 建房(mode=local)
- **THEN** 回傳雙方玩家 token 與初始狀態,行為等同 v1 hotseat

#### Scenario: 帶自訂牌組建房
- **WHEN** 客戶端 POST 建房並附上合法的 32 頁自訂牌組
- **THEN** 建房成功;開局後該玩家的魔本為其自訂內容

#### Scenario: 非法牌組被拒
- **WHEN** 建房牌組將上級卡置於第 3 頁
- **THEN** 回應 422 與違規原因碼(deck.superior_page),不建立房間

### Requirement: 加入房間與開局
系統 SHALL 提供加入端點:以房號換取第二位玩家的 token,並可附上加入者自己的牌組(缺省 level1;自訂牌組 MUST 通過構築規則驗證,違規回 422 且不佔用玩家位)。雙方到齊即以**各自的牌組**建立引擎對局並向所有連線廣播開局。已滿的房間 MUST 拒絕再加入為玩家(仍可觀戰);不存在的房號 MUST 回 404。

#### Scenario: 對手加入即開局
- **WHEN** 第二位玩家以房號 POST join
- **THEN** 回傳其 player_token,雙方 WebSocket 均收到開局狀態

#### Scenario: 雙方各用自己的牌組
- **WHEN** 建房者與加入者各附上不同的合法牌組
- **THEN** 開局後兩人的魔本內容互異,各自視角只見自己的翻開頁內容

#### Scenario: 滿房拒絕第三位玩家
- **WHEN** 已有兩位玩家的房間再收到 join
- **THEN** 回應錯誤,房內對局不受影響

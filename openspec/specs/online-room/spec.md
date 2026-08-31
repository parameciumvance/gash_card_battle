# online-room — 房間生命週期與線上身分

## Purpose

房號約戰、無帳號。Room 包裹既有 Game;token 即身分;計時器與逾時代打在 API 層,引擎無感。
## Requirements
### Requirement: 建立房間
系統 SHALL 提供建房端點:指定模式(online/local)、計時選項(關/30/60/120 秒)、可選的牌組(缺省為 level1 預組;自訂牌組為 32 個卡號的頁序,本機房可為雙方各指定一副)與**可選的玩家暱稱**(線上房為建房者、本機房可為雙方各一;缺省沿用預設「玩家N」),回傳房號(6 碼英數)、建房者的玩家 token、加入連結與觀戰連結。暱稱 MUST 於受理前清理(去頭尾空白、移除控制字元、限長);清理後為空 SHALL 視為未設(顯示回退預設)。自訂牌組 MUST 於受理前以構築規則驗證,違規回 422 與對應原因碼。線上房 MUST 於第二位玩家加入後才建立對局並開局;本機房 MUST 立即開局並一次回傳雙方 token。牌組與暱稱 MUST 只存在於房間生命週期內,伺服器不持久化。

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

#### Scenario: 帶暱稱建房
- **WHEN** 建房者附上暱稱「阿賢」
- **THEN** 房間記錄該暱稱;之後的房間 meta 回應含此暱稱

#### Scenario: 空白或過長暱稱清理
- **WHEN** 暱稱為純空白、或超過長度上限、或含控制字元
- **THEN** 清理後為空者視為未設(顯示預設),過長者截斷至上限,控制字元被移除

### Requirement: 加入房間與開局
系統 SHALL 提供加入端點:以房號換取第二位玩家的 token,可附上加入者自己的牌組(缺省 level1;自訂牌組 MUST 通過構築規則驗證,違規回 422 且不佔用玩家位)與**可選暱稱**(清理規則同建房)。雙方到齊即以各自的牌組建立引擎對局並向所有連線廣播開局。已滿的房間 MUST 拒絕再加入為玩家(仍可觀戰);不存在的房號 MUST 回 404。

#### Scenario: 對手加入即開局
- **WHEN** 第二位玩家以房號 POST join
- **THEN** 回傳其 player_token,雙方 WebSocket 均收到開局狀態

#### Scenario: 雙方各用自己的牌組
- **WHEN** 建房者與加入者各附上不同的合法牌組
- **THEN** 開局後兩人的魔本內容互異,各自視角只見自己的翻開頁內容

#### Scenario: 加入者帶暱稱
- **WHEN** 加入者附上暱稱「小美」
- **THEN** 房間記錄玩家 1 的暱稱;雙方畫面皆以該暱稱顯示玩家 1

#### Scenario: 滿房拒絕第三位玩家
- **WHEN** 已有兩位玩家的房間再收到 join
- **THEN** 回應錯誤,房內對局不受影響

### Requirement: token 即身分
所有指令與連線 SHALL 以 token 鑑別:伺服器由 token 推導玩家索引並填入指令,payload 中自報的 player 欄位 MUST 被忽略;無效 token MUST 被拒絕。觀戰 token MUST 不可提交任何指令。

#### Scenario: 冒名指令無效
- **WHEN** 玩家 A 以自己的 token 提交 payload 標示 player=B 的指令
- **THEN** 指令以 A 的身分處理(或因非 A 的時機而被拒),B 的狀態不受影響

#### Scenario: 觀戰者不能出招
- **WHEN** 持觀戰 token 提交指令
- **THEN** 回應 403,對局狀態不變

### Requirement: 回合計時與逾時代打
房間設定計時器時,系統 SHALL 追蹤「目前等待輸入的玩家」並於其改變時重置期限;逾時 MUST 由伺服器代送該局面的安全預設指令(開始階段=不翻頁、行動權=pass、戰鬥開始確認=迎戰、防禦=不防禦、保護=不保護、硬幣=保留、付費重擲=放棄、選擇類=第一個選項),經正常提交路徑處理並於事件標記逾時。逾時 MUST NOT 直接判負。

#### Scenario: 逾時自動 pass
- **WHEN** 非戰鬥中輪到玩家行動且超過房間計時秒數無指令
- **THEN** 伺服器代送 pass,事件帶逾時標記,對局繼續

#### Scenario: 決策逾時採安全預設
- **WHEN** 保護決策等待超時
- **THEN** 伺服器代送「不保護」,傷害正常結算

#### Scenario: 計時器關閉時不逾時
- **WHEN** 房間 timer=關,玩家長時間無動作
- **THEN** 不發生任何代打

### Requirement: 斷線重連
玩家重新連線 SHALL 能無損續打:以 token 重建 WebSocket 即取得完整視角快照與下一事件序號;`events?since=N` 增量回放 MUST 與推送內容一致(同樣經視角過濾)。對局 MUST NOT 因斷線而暫停或判負(計時器照常計時)。

#### Scenario: 重連取回全量狀態
- **WHEN** 玩家瀏覽器重整後以原 token 重連
- **THEN** 收到 welcome(含視角快照與 next_seq),畫面完整重建,可立即行動

### Requirement: 觀戰
持觀戰連結者 SHALL 可隨時進房觀看:僅公開資訊視角(雙方翻開頁內容均不可見)、事件推送同樣過濾;觀戰人數不限;觀戰者的加入與離開 MUST NOT 影響對局。

#### Scenario: 觀戰視角無手牌
- **WHEN** 觀戰者連線至進行中的對局
- **THEN** 快照中雙方 open_pages 僅含頁碼,無卡號與費用


## MODIFIED Requirements

### Requirement: 建立房間
系統 SHALL 提供建房端點:指定模式(online/local/npc)、計時選項(關/30/60/120 秒;NPC 房不使用計時器)、可選的牌組(缺省為 level1 預組;自訂牌組為 32 個卡號的頁序,本機房可為雙方各指定一副;NPC 房的 NPC 牌組見「NPC 房」)與**可選的玩家暱稱**(線上房與 NPC 房為建房者、本機房可為雙方各一;缺省沿用預設「玩家N」),回傳房號(6 碼英數)、玩家 token 與觀戰連結;線上房另回傳加入連結。暱稱 MUST 於受理前清理(去頭尾空白、移除控制字元、限長);清理後為空 SHALL 視為未設(顯示回退預設)。自訂牌組 MUST 於受理前以構築規則驗證,違規回 422 與對應原因碼。線上房 MUST 於第二位玩家加入後才建立對局並開局;本機房 MUST 立即開局並一次回傳雙方 token;NPC 房 MUST 立即開局並只回傳玩家的 token。牌組與暱稱 MUST 只存在於房間生命週期內,伺服器不持久化。

#### Scenario: 建立線上房
- **WHEN** 客戶端 POST 建房(mode=online, timer=60)
- **THEN** 回傳房號、player_token、join_url、spectate_url,且對局尚未開始

#### Scenario: 本機房立即開局
- **WHEN** 客戶端 POST 建房(mode=local)
- **THEN** 回傳雙方玩家 token 與初始狀態,行為等同 v1 hotseat

#### Scenario: NPC 房立即開局
- **WHEN** 客戶端 POST 建房(mode=npc)
- **THEN** 回傳房號、一個 player_token、spectate_url 與初始狀態,不含 join_url

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

## ADDED Requirements

### Requirement: NPC 房
建房模式為 `npc` 時,建房者 SHALL 為玩家 0、NPC 為玩家 1。請求 SHALL 可指定 NPC 難度(`dummy` / `normal`,見 `npc-opponent`「NPC 難度」;缺省 `normal`,其他值回 422)與 NPC 牌組:指定一副(格式同建房牌組),或提供候選牌組清單,由伺服器從中隨機抽一副(抽選由房間 seed 決定);兩者皆未提供時 NPC 使用 level1,兩者同時提供回 422。指定的 NPC 牌組與每副候選 MUST 以構築規則驗證,任一違規回 422 且不建立房間。NPC 房 MUST NOT 可加入為玩家(回 409),MUST NOT 使用計時器(請求的計時選項不採用)。玩家 token 的視角 SHALL 與線上房相同,看不到 NPC 翻開頁的內容。房間 meta SHALL 標示 NPC 的座位與難度。NPC 使用的牌組 MUST NOT 在對局結束前出現在任何回應中;對局結束後 SHALL 於房間 meta 公開(預組以其 id、自訂牌組以其頁序)。

#### Scenario: NPC 房的座位與難度
- **WHEN** 客戶端 POST 建房(mode=npc, npc_level=dummy)
- **THEN** 房間 meta 標示玩家 1 為 NPC、難度 dummy,且沒有計時期限

#### Scenario: 指定 NPC 牌組
- **WHEN** 建 NPC 房時指定一副合法的 NPC 牌組
- **THEN** NPC 的魔本為該牌組

#### Scenario: 隨機 NPC 牌組
- **WHEN** 建 NPC 房時提供 3 副合法的候選牌組
- **THEN** NPC 的魔本為其中一副;以相同 seed 再建一次,抽到同一副

#### Scenario: 非法 NPC 牌組被拒
- **WHEN** 指定的 NPC 牌組或任一候選牌組違反構築規則,或難度不是 dummy / normal
- **THEN** 回應 422,不建立房間

#### Scenario: 對局中不公開 NPC 牌組
- **WHEN** NPC 房的對局進行中,玩家查詢房間狀態或收到推送
- **THEN** 回應不含 NPC 使用的牌組,NPC 翻開頁只有頁碼

#### Scenario: 對局結束後公開 NPC 牌組
- **WHEN** NPC 房的對局結束
- **THEN** 房間 meta 含 NPC 使用的牌組(預組 id 或頁序)

#### Scenario: NPC 房不可加入
- **WHEN** 有人對 NPC 房 POST join
- **THEN** 回應 409,對局不受影響

### Requirement: NPC 座位的驅動
NPC 房中,每當等待輸入的玩家是 NPC(開局後、玩家指令被接受後、金手指套用後),系統 SHALL 讓 NPC 經與玩家相同的提交路徑連續送出指令,直到等待的不是 NPC 或對局結束;NPC 指令產生的事件 SHALL 與玩家指令一樣推送給房間所有連線。NPC 每次送出前 SHALL 稍候,讓玩家看清前一個行動:pass、迎戰、不防禦等不改變盤面的指令等待較短,其他指令較長。等待期間局面有變化(如套用金手指)時,NPC SHALL 依新局面重新決定。同一房間 MUST 同時只有一個 NPC 驅動;驅動因故中斷時,系統 SHALL 自動恢復,MUST NOT 讓對局永久停在等待 NPC。

#### Scenario: 玩家行動後 NPC 接手
- **WHEN** NPC 房中玩家在非戰鬥行動權 pass
- **THEN** NPC 隨後送出指令,玩家的 WebSocket 收到 NPC 行動的推送

#### Scenario: 開局即輪到 NPC
- **WHEN** NPC 房開局時先攻玩家為 NPC
- **THEN** NPC 自動進行開始階段與行動,直到輪到玩家

#### Scenario: NPC 送出前稍候
- **WHEN** NPC 依序送出 pass 與宣告攻擊
- **THEN** 兩個指令送出前都有等待,pass 的等待較短

#### Scenario: 等待期間套用金手指
- **WHEN** NPC 等待送出時玩家套用金手指
- **THEN** NPC 依套用後的局面決定要送出的指令

#### Scenario: 同一決策點只送出一次
- **WHEN** 玩家指令被接受與伺服器的定期檢查幾乎同時觸發 NPC
- **THEN** NPC 對同一決策點只送出一個指令

# online-room — 房間生命週期與線上身分

房號約戰、無帳號。Room 包裹既有 Game;token 即身分;計時器與逾時代打在 API 層,引擎無感。

## ADDED Requirements

### Requirement: 建立房間
系統 SHALL 提供建房端點:指定模式(online/local)與計時選項(關/30/60/120 秒),回傳房號(6 碼英數)、建房者的玩家 token、加入連結與觀戰連結。線上房 MUST 於第二位玩家加入後才建立對局並開局;本機房 MUST 立即開局並一次回傳雙方 token。

#### Scenario: 建立線上房
- **WHEN** 客戶端 POST 建房(mode=online, timer=60)
- **THEN** 回傳房號、player_token、join_url、spectate_url,且對局尚未開始

#### Scenario: 本機房立即開局
- **WHEN** 客戶端 POST 建房(mode=local)
- **THEN** 回傳雙方玩家 token 與初始狀態,行為等同 v1 hotseat

### Requirement: 加入房間與開局
系統 SHALL 提供加入端點:以房號換取第二位玩家的 token;雙方到齊即建立引擎對局並向所有連線廣播開局。已滿的房間 MUST 拒絕再加入為玩家(仍可觀戰);不存在的房號 MUST 回 404。

#### Scenario: 對手加入即開局
- **WHEN** 第二位玩家以房號 POST join
- **THEN** 回傳其 player_token,雙方 WebSocket 均收到開局狀態

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
房間設定計時器時,系統 SHALL 追蹤「目前等待輸入的玩家」並於其改變時重置期限;逾時 MUST 由伺服器代送該局面的安全預設指令(開始階段=不翻頁、行動權=pass、戰鬥開始確認=讓過、防禦=不防禦、庇護=不庇護、硬幣=保留、付費重擲=放棄、選擇類=第一個選項),經正常提交路徑處理並於事件標記逾時。逾時 MUST NOT 直接判負。

#### Scenario: 逾時自動 pass
- **WHEN** 非戰鬥中輪到玩家行動且超過房間計時秒數無指令
- **THEN** 伺服器代送 pass,事件帶逾時標記,對局繼續

#### Scenario: 決策逾時採安全預設
- **WHEN** 庇護決策等待超時
- **THEN** 伺服器代送「不庇護」,傷害正常結算

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

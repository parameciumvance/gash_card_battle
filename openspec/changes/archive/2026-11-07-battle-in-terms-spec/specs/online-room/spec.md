# Spec Delta

## MODIFIED Requirements

### Requirement: 回合計時與逾時代打
房間設定計時器時,系統 SHALL 追蹤「目前等待輸入的玩家」並於其改變時重置期限;逾時 MUST 由伺服器代送該局面的安全預設指令(開始階段=不翻頁、行動權=pass、進入戰鬥確認=同意進入戰鬥、防禦=不防禦、保護=不保護、硬幣=保留、付費重擲=放棄、選擇類=第一個選項),經正常提交路徑處理並於事件標記逾時。逾時 MUST NOT 直接判負。

#### Scenario: 逾時自動 pass
- **WHEN** 非戰鬥中輪到玩家行動且超過房間計時秒數無指令
- **THEN** 伺服器代送 pass,事件帶逾時標記,對局繼續

#### Scenario: 決策逾時採安全預設
- **WHEN** 保護決策等待超時
- **THEN** 伺服器代送「不保護」,傷害正常結算

#### Scenario: 計時器關閉時不逾時
- **WHEN** 房間 timer=關,玩家長時間無動作
- **THEN** 不發生任何代打

### Requirement: NPC 座位的驅動
NPC 房中,每當等待輸入的玩家是 NPC(開局後、玩家指令被接受後、金手指套用後),系統 SHALL 讓 NPC 經與玩家相同的提交路徑連續送出指令,直到等待的不是 NPC 或對局結束;NPC 指令產生的事件 SHALL 與玩家指令一樣推送給房間所有連線。NPC 每次送出前 SHALL 稍候,讓玩家看清前一個行動:pass、同意進入戰鬥、不防禦等不改變盤面的指令等待較短,其他指令較長。等待期間局面有變化(如套用金手指)時,NPC SHALL 依新局面重新決定。同一房間 MUST 同時只有一個 NPC 驅動;驅動因故中斷時,系統 SHALL 自動恢復,MUST NOT 讓對局永久停在等待 NPC。

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

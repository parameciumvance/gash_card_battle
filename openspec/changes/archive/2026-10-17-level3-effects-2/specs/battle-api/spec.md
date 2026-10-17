## MODIFIED Requirements

### Requirement: 狀態快照與資訊隱藏
狀態快照 SHALL 依觀看者(player0/player1/觀戰)產生:包含渲染所需完整公開狀態(階段、行動權、雙方 MP、場面、魔書進度、戰鬥子狀態、pending 的 kind、決策者與來源卡號(`source`,無來源時為 null)、事件序號、雙方玩家暱稱)。對手與觀戰者的回應中,任一玩家未翻開頁的內容 MUST NOT 出現(僅頁碼/張數);翻開頁的卡片內容 MUST 只對持有者可見,對手與觀戰者僅見頁碼——**唯一例外:已宣告攻防戰術的「使用中頁」(攻擊宣告 `battle_in` 的攻方頁、戰鬥中 `battle` 的攻方 `attack_page` 與防方 `defense_page`)SHALL 對所有視角含卡片內容並標記 `in_use`(宣告即公開);戰鬥結束後 MUST 恢復僅頁碼**;另一例外:對手場上有 P-024 時,該對手(P-024 的持有者)SHALL 看得到此玩家翻開頁的卡片內容;翻開頁中的事件卡 SHALL 附加成後的費用(`cost`,含對手 M-040 的 +1),與戰術卡相同;持有者本人的視角 MAY 含自己完整魔書內容(`book`,全 32 頁順序)——此為己方隱藏資訊,規則上持有者本就已知,MUST NOT 出現在對手或觀戰者的回應中;pending 的選項細節 MUST 只對決策者可見。本機模式的 client 持有雙方 token,視為全視角(雙方 book 皆含)。

#### Scenario: 對手未翻頁內容不外洩
- **WHEN** 玩家 A 查詢狀態
- **THEN** 玩家 B 的未翻開頁僅以頁碼/張數表示,B 的 `book` 完整內容 MUST NOT 出現在 A 的回應中

#### Scenario: 己方全魔書對本人可見
- **WHEN** 玩家 A 查詢狀態
- **THEN** A 自己的 player_view 含 `book`(全 32 頁卡號),搭配 consumed_pages/pos 足以標示每頁狀態

#### Scenario: 觀戰者看不到任一方魔書內容
- **WHEN** 觀戰者查詢狀態
- **THEN** 雙方的未翻開頁與 `book` 完整內容皆不出現,僅見頁碼與公開場面

#### Scenario: 對手翻開頁不可見
- **WHEN** 玩家 A 查詢狀態且 B 無宣告中的攻防戰術
- **THEN** 玩家 B 的 open_pages 僅含頁碼,無卡號與費用;A 自己的 open_pages 完整

#### Scenario: 宣告中的攻擊戰術對對手可見
- **WHEN** 玩家 B 以第 9 頁的戰術宣告攻擊(battle_in 或 battle 進行中),玩家 A 查詢狀態
- **THEN** A 看到 B 的第 9 頁含卡號並標記 `in_use`;B 其餘翻開頁仍僅頁碼

#### Scenario: 防禦戰術同樣揭露且歸屬正確
- **WHEN** 戰鬥中防方 A 以第 5 頁宣告防禦,觀戰者查詢狀態
- **THEN** A 的第 5 頁與攻方的攻擊頁皆含卡號;攻方頁不會誤掛在防方(反之亦然)

#### Scenario: 戰鬥結束恢復保密
- **WHEN** 該場戰鬥結算完畢(battle 清空)後對手查詢狀態
- **THEN** 原使用中頁恢復僅頁碼(無卡號、無 `in_use`)

#### Scenario: 決策選項只送決策者
- **WHEN** M-011 效果等待玩家 A 從 B 的魔書挑選魔物
- **THEN** 只有 A 的視角含選項(頁碼與卡號);B 與觀戰者僅見「A 決策中」

#### Scenario: 快照可完整重繪
- **WHEN** 前端重新整理後以 token 查詢狀態
- **THEN** 回應足以完整重建該視角畫面(含行動 log 與暱稱),無需重放指令

#### Scenario: P-024 公開翻開頁
- **WHEN** 玩家 A 場上有 P-024,A 查詢狀態
- **THEN** B 的 open_pages 含卡號;觀戰者與 B 自己的視角規則不變

#### Scenario: 事件卡費用含加成
- **WHEN** 玩家 A 場上有 M-040,B 翻開費用 0 的事件卡,B 查詢狀態
- **THEN** 該頁的 `cost` 為 1


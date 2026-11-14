# tutorial — 設計

## 檔案分工

| 位置 | 內容 |
|---|---|
| `data/tutorial/player.json`、`opponent.json` | 教學局面的雙方魔書。不放在 `data/decks/`,以免出現在預組清單 |
| `src/gash/tutorial/__init__.py` | `tutorial_decks()`、`TailsRng`(擲硬幣一律反面)、`opponent_commands(game, seat)`(腳本對手的候選指令) |
| `src/gash/api/rooms.py`、`app.py` | 房間模式 `tutorial`、建房、`tutorial_hold` 與 `POST /api/rooms/{code}/tutorial/continue`、`_npc_decide` 依 `level` 分派 |
| `frontend/tutorial.js` | 步驟表 `TUTORIAL_STEPS`、鎖定(`tutorialAllows`)、對手放行(`tutorialRelease`)、教學面板(`renderTutorial`)、開始與離開 |
| `frontend/app.js` | 掛點:`send()` 開頭呼叫 `tutorialAllows`、`applyPayload` 呼叫 `tutorialUpdate`、`render()` 結尾呼叫 `renderTutorial`;首頁入口;自動 pass 與棄權鈕在教學中關閉 |

## 行為決定與理由

### 教學房沿用 NPC 房的座位與驅動

**相關規格:** 「教學對局的開始」「對手腳本的節奏」

**決定:** 教學房是房間模式 `tutorial`。NPC 座位的 `level = "tutorial"`,`_npc_decide` 呼叫腳本 `opponent_commands`,其餘(驅動 task、出手間隔、廣播、聚焦展示、關閉時取消驅動)與 NPC 房相同。先攻固定為玩家(`first_player=0`,記錄的原因為 `tutorial`)。不計時;金手指只開放本機房與 NPC 房,教學房自然沒有。

**理由:** 不讓前端代送對手指令(要拿雙方 token、快照視角會混在一起),也不另做一套驅動。

**確認狀態:** `Confirmed`(tutorial change,2026-11-14)

### 對手腳本依盤面決定

**相關規格:** 「自由步驟的偏離」

**決定:** `opponent_commands` 只看當下狀態:
- 開始階段翻 1 張。
- 自己回合的非戰鬥中,翻開的頁有可用的ジキル就宣告攻擊,否則 pass。
- 被攻擊時有可用的ジキル就防禦。回合 1 因 P-001 不能防禦,引擎會拒絕,`submit_ranked` 退回安全預設的不防禦。
- 其餘(進入戰鬥確認、效果步驟、保護等決策)交給安全預設。

**理由:** 只有關鍵步驟鎖定,玩家在自由步驟可能提早 pass、選擇保護與否;對手照狀態行動,劇本才接得下去。`tests/test_tutorial.py` 涵蓋保護三種分支與提早 pass。

**確認狀態:** `Confirmed`

### 對手的節奏:每個玩家指令後暫停,由前端放行

**相關規格:** 「對手腳本的節奏」

**決定:**
- 教學房裡玩家每送出一個指令,伺服器就設 `tutorial_hold = True`,對手不出手。
- 前端在輪到對手時呼叫 `tutorial/continue` 放行(每個盤面一次);目前步驟是要先讀完的說明(`next`)時不呼叫,等玩家按「下一步」。
- 放行後對手一路出手到輪到玩家為止。

**理由:** NPC 原本的出手間隔對教學太快,讀不完說明。若改由前端在顯示說明時才暫停,玩家送出指令後對手可能搶在前面出手(競態)。

**確認狀態:** `Confirmed`

### 步驟判斷與鎖定在前端

**相關規格:** 「教學步驟的鎖定」

**決定:**
- 每一步的完成條件依快照與「這一步開始後」的事件判斷,步驟索引只往前不往後,存在 sessionStorage(重新整理後恢復)。
- 鎖定在 `send()` 開頭攔截:目前步驟有要求的操作、而且玩家還沒做到時,其他指令不送出,以 toast 提示並搖動面板。做到之後同一步的其他操作(例如攻擊後在效果步驟 Pass)照常。
- 自動 pass 在教學中關閉,因為自動回應會繞過鎖定。

**理由:** 入口很多、每次重繪都會重建,不逐一停用按鈕(理由同 battle-ui 的 `sending`)。

**確認狀態:** `Confirmed`

### 說明文字

**相關規格:** 「教學的語言」

**決定:**
- 說明裡的卡名以 `cname()` 帶入,依各語言的卡片文字檔(例如中文 P-001 是代理版的「高嶺清人」)。按鈕名稱以 `ui.*` 帶入,和畫面上一致。
- 第 8 步插入行動的理由:翻開頁的セウシル是ティオ的戰術,場上還沒有ティオ,就算進入戰鬥也沒有魔物能使用它,所以先插入行動放出ティオ(使用者指定的教學重點)。
- 第 13 步依盤面切換:第 11 步讓魔書受傷時,已經翻到ブリ與ザケル的對頁,改說「傷害也會翻魔書」。
- 簡中由 `tools/build_zh_cn.py` 從繁中產生。

**確認狀態:** `Confirmed`

## 已知限制

- 前端的步驟判斷依賴事件名稱(`battle_ended`、`coin_flipped` 等)與快照的形狀;改動時要跑 `tests/test_tutorial_ui.py`(走完全程的測試標 `slow`)。
- 劇本的數字(8000 對 6000、6000 平手、+1000 勝出)依賴 M-001、Ex-005、S-022、M-021、S-037 的資料與效果;卡片資料或效果改動時,`tests/test_tutorial.py` 會直接驗證這些數字。

## Why

目前只能和真人對戰(線上房)或一人操作雙方(本機測試模式);單機發行版的玩家沒有對手時無法真正玩一局,測試效果時也得自己操作對手。專案負責人的 todo 列有「NPC對戰」,本變更提供由伺服器驅動的 NPC 對手。

## What Changes

- 新增 NPC 對戰房(`mode="npc"`):建房即開局,玩家為玩家 0,NPC 坐玩家 1;玩家以一般(非全視角)視角對戰,看不到 NPC 的翻開頁。
- NPC 由伺服器在輪到它時代為決策,指令走與玩家相同的提交路徑;引擎不變。
- 兩種難度:
  - 木人樁:沿用逾時代打的安全預設(不翻頁、pass、不防禦、選不使用),供練習與配合金手指測試效果。
  - 一般:對每個合法行動做「一步 + 模擬到塵埃落定」的前瞻,以評估函式選擇。
- NPC 看不到隱藏資訊:決策只取決於 NPC 視角可見的資訊與 NPC 自己的隨機來源(不讀對手翻開頁、魔本順序,也不預知擲幣)。
- NPC 牌組可選預組或玩家自己儲存的牌組,可指定或隨機;隨機時對局中不公開抽到哪一副,對局結束後公開。
- NPC 房不使用計時器;開放金手指(與本機測試模式相同)。
- 首頁新增 NPC 對戰入口(我的牌組、NPC 牌組或隨機、難度)。

## Capabilities

### New Capabilities

- `npc-opponent`:NPC 的決策——資訊可見範圍(公平性)、只送出引擎接受的指令、難度與基本合理性、可重現性。

### Modified Capabilities

- `online-room`:「建立房間」新增 NPC 房模式(立即開局、NPC 牌組指定或隨機、無計時器);新增 NPC 座位的驅動(輪到 NPC 時代為提交、行動節奏、牌組公開時機)。
- `local-test-mode`:「金手指端點僅限本機模式」放寬為本機房與 NPC 房。
- `battle-ui`:「首頁入口」新增 NPC 對戰入口與其對局呈現;「金手指面板」在 NPC 房也提供。

## Impact

- 程式:
  - 新增 `src/gash/npc/`(決策、隱藏資訊替換、評估)。
  - `src/gash/api/app.py`、`rooms.py`:NPC 房建立、NPC 驅動、金手指模式檢查。
  - `frontend/app.js`、`index.html`、`style.css`、`i18n/zh-TW.json`:NPC 對戰入口、金手指入口條件、NPC 牌組公開顯示。
- 引擎(`src/gash/engine/`)不改規則;NPC 只透過 `submit` 與狀態副本使用引擎。`awaited_player` / `default_command` 從 `api/rooms.py` 移到 `engine/awaiting.py`,讓 NPC 不依賴 api 層,行為不變。
- 效能:NPC 在伺服器的 event loop 中同步思考,需限制每次決策的時間,避免影響同一台伺服器的其他房間。
- 文件:新 capability `npc-opponent` 的 spec 與 design、capability map、README。

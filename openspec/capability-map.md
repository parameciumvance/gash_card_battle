# Capability Map

規格制度見 `docs/specification-guide.md`。本檔是導航用的概觀,詳細行為在各 capability 的 `spec.md`,設計與理由在 `design.md`。

## 系統概觀

《金色のガッシュベル!! THE CARD BATTLE》的對戰網頁。單一 Python 服務(FastAPI)提供 API 與靜態前端;遊戲規則由純 Python 引擎執行,房間狀態存在行程記憶體。可和真人線上對戰、一人操作雙方測試,或和伺服器驅動的 NPC 對戰。可在 VPS 以容器長期部署,或以單機發行版在玩家電腦上執行。

| 子系統 | Capabilities |
|---|---|
| 遊戲核心 | `game-engine`、`card-effects`、`effect-tree` |
| 卡片資料 | `card-data` |
| 對戰服務 | `online-room`、`battle-api`、`local-test-mode`、`npc-opponent` |
| 前端 | `battle-ui`、`deck-builder` |
| 發行與部署 | `standalone-release`、`docker-deployment` |

## Capabilities

覆蓋程度依指南 §10.1,相對於各 spec `## Purpose` 宣告的 scope 判斷。標「初評」者尚未逐項比對程式與測試,之後的 change 碰到時再修正。

| Capability | 責任 | Spec 覆蓋 | Design 覆蓋 | 備註 |
|---|---|---|---|---|
| `game-engine` | 遊戲規則:階段、行動權、戰鬥流程、傷害與保護、勝敗、中途決策 | Partial | Partial | 初評。規則依 `ref/raw/rule3.md`;design 只有架構與 pending |
| `card-effects` | 第一、二彈全部卡片的效果行為,效果原語、持續效果、待命、被動觸發 | Partial | Partial | 逐卡行為以日文效果文為準,spec 情境只列解讀與易錯處;design 只整理了效果樹遷移以來的機制與解讀 |
| `effect-tree` | 卡片效果的執行機制:節點、直譯器、續體、登記入口 | Documented | Documented | 每條需求都有對應測試(`tests/test_effect_tree.py`,擲幣確認鏈另見 `tests/test_effect_characterization.py`) |
| `card-data` | 日文權威來源抓取、`cards.json` 轉換、各語言卡片文字檔(`cards.<lang>.json`,簡中由繁中產生)、卡圖資產、預組魔本資料 | Partial | Partial | 初評;design 只整理了卡片文字檔 |
| `online-room` | 房號約戰、token 身分、回合計時與逾時代打、斷線重連、觀戰、NPC 房與 NPC 座位的驅動 | Partial | Partial | 初評;design 只整理了等待者與 NPC 座位 |
| `battle-api` | 房間內對局的指令轉發、視角化快照與事件、WebSocket 推送 | Partial | Partial | 初評;design 只整理了快照的公開 / 私有界線 |
| `local-test-mode` | 本機房與 NPC 房的金手指端點 | Partial | Partial | 初評;design 只有行為決定與理由 |
| `npc-opponent` | NPC 對手的決策:資訊可見範圍、只送出引擎接受的指令、難度與基本判斷、可重現 | Documented | Documented | 測試在 `tests/test_npc.py`;NPC 房與驅動見 `online-room` |
| `battle-ui` | 對戰畫面:首頁與設定頁、盤面、回合與時機指示、操作與決策、行動記錄、動畫與聚焦展示、演出設定、規則頁、意見回報、語言選擇(繁中、簡中、英、日)與 i18n | Partial | Partial | 初評;design 只整理了首頁與設定頁、事件動畫、聚焦展示、回合和時機指示、規則頁、意見回報與語言 |
| `deck-builder` | 魔本構築:對頁編輯、合法性提示、瀏覽器儲存、文字碼 | Partial | Not documented | 初評 |
| `standalone-release` | 單機發行:資源目錄解析、啟動器、公開通道、打包 | Partial | Not documented | 初評 |
| `docker-deployment` | VPS 容器部署:映像檔、Cloudflare Tunnel 對外、CI 分流、自動更新 | Partial | Partial | 初評;design 整理了架構、映像檔、發布與更新、對外服務 |

## 重要關係與 flow

### 對戰指令

```text
battle-ui ──指令──▶ battle-api(online-room 驗證 token、計時)
                        │
                        ▼
                   game-engine.submit ──事件──▶ battle-api 依觀看者過濾 ──WebSocket──▶ battle-ui
```

- 引擎是唯一的規則權威;`battle-api` 只轉發與過濾,不判斷規則。
- 逾時代打由 `online-room` 產生預設指令,走同一條路徑。

### NPC 對戰

```text
online-room 的 NPC 驅動(輪到 NPC 時)
        │ decide
        ▼
npc-opponent ──只經 determinize 取得盤面副本(對手隱藏資訊換成抽樣)──▶ 在副本上試送、模擬、評估
        │ 排序好的候選
        ▼
game-engine.submit(與玩家相同的路徑)──事件──▶ battle-api 過濾 ──WebSocket──▶ battle-ui
```

- `npc-opponent` 持有「NPC 決定送什麼」;`online-room` 持有「何時、以什麼節奏送」。
- 「NPC 看得到什麼」以 `battle-api` 的視角過濾為準。

### 卡片效果

```text
game-engine(規則時點)──查 registry 掛鉤──▶ card-effects 登記的效果 ──由──▶ effect-tree 直譯器執行
```

- `card-effects` 持有「卡片做什麼」;`effect-tree` 持有「效果怎麼執行」;`game-engine` 持有規則與流程。
- `card-effects` 的部分解讀依賴 `game-engine` 的規則,例如「下一場戰鬥」依賴「只有回合玩家能宣告攻擊」。

### 卡片資料

```text
atwiki ──抓取──▶ card-data(cards_ja.csv → cards.json)──▶ game-engine / card-effects 讀卡片定義
                                                     └──▶ deck-builder、battle-ui 顯示與構築
```

- 卡片效果以 `cards.json` 的日文效果文為權威;`cards.zh-TW.json` / `cards.en.json` 的翻譯只供閱讀(英文效果文依日文翻譯,不照卡表),`cards.ja.json` 由 `cards_ja.csv` 產生。

## 建議閱讀入口

| 要做的事 | 從這裡開始 |
|---|---|
| 實作或修改卡片效果 | `card-effects` 的 spec 與 design → `effect-tree/design.md` → `AGENTS.md`「實作 / 修改卡片效果」 |
| 修改遊戲規則或流程 | `game-engine` |
| 修改對戰畫面 | `battle-ui` → `battle-api` → `online-room` |
| 修改 NPC | `npc-opponent` 的 spec 與 design → `online-room/design.md`「NPC 座位」 |
| 部署或發行 | `docker-deployment` / `standalone-release` |

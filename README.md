# 金色のガッシュベル!! THE CARD BATTLE — 對戰網頁

《魔法少年賈修 CCG》規則全自動裁決的同機雙人(hotseat)對戰網頁。
規則依據 [ref/raw/rule3.md](ref/raw/rule3.md),卡池為第一彈(Series 1 Level 1)全 67 種卡。

## 啟動

```bash
pip install -e ".[dev]"
uvicorn gash.api.app:app --reload
# 瀏覽器開 http://127.0.0.1:8000/
```

首頁四個入口:

- **本機對戰**:兩人共用同一畫面輪流操作(全視角),雙方可各選牌組。
- **建立房間**:線上約戰。選擇回合計時(不限時/30/60/120 秒每動作)與自己的牌組後
  產生 6 碼房號、加入連結與觀戰連結;把加入連結傳給朋友,對方選好牌組即開局。
- **加入房間**:輸入朋友給的房號,選自己的牌組後加入。
- **牌組構築**:編排自己的 32 頁魔本(見下)。

## 牌組構築

魔本構築是**排版**:頁位=出牌時機、對頁=同時翻開的手牌、最後一頁的術費用為 0。
構築器以 16 個對頁呈現魔本,左側卡池(可依類型/對應魔物/收錄產品篩選,如 Level 1、The Best Booster 1):

- 點卡池的卡 → 放入選中頁位(或下一空頁);點頁位選中,再點另一頁位=移動/互換(也可拖拉);
  點選中的有卡頁位=移除。
- 七條構築規則即時提示(32 頁全滿、首頁魔物、末頁術、中級 12+、上級 22+、同號 ≤4、魔物 ≤8);
  違規的牌組可以儲存(標記不合法)但不能帶進對戰。伺服器在開局時仍會做最終驗證。
- 牌組存在瀏覽器(localStorage);「匯出牌組碼」產生一行 `gash1:...` 文字,
  可備份或貼給朋友,對方「匯入牌組碼」即得同一副。清瀏覽器資料前記得匯出。

預組「賈修+蒂歐+康裘美」(`data/decks/level1.json`)永遠可選,也可作為構築起手複製。

### 新增一個預設牌組

預組是**資料驅動**的:伺服器啟動時掃描 `data/decks/*.json`,前端從 `GET /api/decks` 取得清單
動態生成選單。新增一個預組 = **丟一個 JSON 檔**(重啟伺服器後生效),不需改任何程式碼。

```jsonc
// data/decks/level3.json
{
  "id": "level3",                    // 唯一識別(建議同檔名)
  "name": "第三彈預組",              // 選單顯示名(最省:只寫這行)
  "pages": ["M-xxx", "S-xxx", ...]   // 32 頁卡號,須通過構築規則(首頁魔物、末頁術…)
}
```

- **顯示名**依序解析:`name_key`(經 i18n 字典 `frontend/i18n/zh-TW.json` 解析,可多語)→ 內嵌 `name` → `id`。
  只要在地化就加 `name_key` 並補各語系 i18n 條目;否則直接寫 `name` 即可。
- 檔案若無法通過構築驗證,啟動掃描時會被排除(記 log),不影響其他預組。
- 請求端只以 `{preset: <id>}` 指定,伺服器用 id 查掃描到的白名單載入,絕不轉為任意檔案路徑。

構築器左側卡池的「產品」篩選(如 Level 2)是依 `cards.json` 每張卡的 `sets` 欄自動產生的,
與預組無關 — 只要卡在卡池裡就能手動構築,新增預組只是多一個「開局即可選的完整 32 頁」捷徑。

線上模式規則與資訊視角:
- 自己永遠顯示在畫面下方;**對手翻開頁只顯示卡背與頁碼**(依原規則,使用時才展示;
  伺服器端過濾,前端拿不到資料)。E-014/M-011 的檢視效果只對使用者本人揭露內容。
- 斷線重連:重新整理頁面即自動續打(token 存於瀏覽器 localStorage)。
- 回合計時開啟時,逾時由伺服器代打安全動作(pass/不防禦/不庇護等),不判負;
  行動記錄會標示「逾時代打」。
- 觀戰連結可分享給任意人數,觀戰者看不到任何一方的翻開頁內容。

限制:對局存在伺服器記憶體,**伺服器重啟即失局**;房間閒置 2 小時自動回收;無帳號與配對。

## 測試

```bash
python -m pytest        # 引擎規則、67 張卡逐卡效果、API 整合、整局劇本
```

## 專案結構

```
src/gash/
  engine/               純 Python 遊戲引擎(無 IO,指令進 → 事件出)
    state.py            狀態模型:魔本頁序、MP、魔物槽、modifier、待命、戰鬥子狀態
    engine.py           規則主體:階段流程、輪流行動權、戰鬥五步驟、傷害/庇護、勝敗
    cards.py / deck.py  卡片定義載入、魔本構築合法性驗證
    effects/            效果系統
      registry.py       引擎 ↔ 卡片效果的掛鉤介面
      primitives.py     效果原語(加魔力、禁止旗標、待命、互動式硬幣…)
      mamodo.py / partners.py / events.py / spells.py   逐卡 handler
  api/
    app.py              FastAPI:房間端點、指令轉發、WebSocket 推送、逾時代打
    rooms.py            房間模型、token 身分、計時器(等待者推導與安全預設指令)
    views.py            視角過濾:snapshot(game, viewer) 與事件過濾(資訊不外洩的單點)
frontend/               無框架靜態前端(中文 UI,文字全走 i18n 字典)
  i18n/zh-TW.json       介面文字與行動記錄模板
  assets/cards/         卡圖(缺圖時自動以文字卡面呈現)
data/
  cards.json            67 種卡結構化數值資料(由 xlsx 抽取,e/j 差異採日版 j)
  cards.zh-TW.json      卡片中文文本(卡名/效果),獨立於數值、可自由校對
  decks/level1.json     預組魔本(32 頁)
tools/
  extract_cards.py      xlsx → cards.json 抽取(開發工具,一次性)
  download_images.py    卡圖批次下載(Google Drive,支援續抓與失敗清單)
```

## 資料管線

1. `ref/raw/Zatch Bell CCG List for TTS.xlsx` 為卡片資料來源(唯讀)。
2. `python tools/extract_cards.py` 過濾 Series 1 Level 1、e/j 去重(採日版 j)、
   自儲存格超連結取得卡圖網址,輸出 `data/cards.json`(67 種)。
3. `python tools/download_images.py` 批次下載卡圖至 `frontend/assets/cards/{卡號}.jpg`;
   已存在自動跳過,失敗清單寫入 `_failed.txt`,缺圖不影響遊戲。

## 翻譯校對

卡片中文文本集中在 `data/cards.zh-TW.json`,以卡號為 key:

```json
"S-001": {"name": "札克爾", "name_ja": "ザケル", "attr": "雷", "effect": "…"}
```

改動此檔只影響顯示,不影響任何遊戲邏輯;介面用語則在 `frontend/i18n/zh-TW.json`。
未來新增語言 = 並列新增 `cards.<lang>.json` 與 `i18n/<lang>.json`。

## 架構備註

- 後端為權威伺服器:規則、隨機數、狀態、資訊過濾全在伺服器;前端只渲染視角化快照與送指令。
- 身分 = token:指令帶 `X-Player-Token`,伺服器由 token 決定玩家,payload 自報身分無效。
- 事件流帶全域序號:`GET /api/rooms/{code}/events?since=N` 增量同步(同樣經視角過濾),
  WebSocket 推送與 HTTP 回應以序號冪等,斷線重連即補齊。
- 視角過濾收斂在 `api/views.py` 單點:未翻開頁對所有人保密、翻開頁只對持有者可見、
  決策選項只送決策者、觀戰為純公開視角。引擎完全不知道「視角」存在。

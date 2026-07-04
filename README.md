# 金色のガッシュベル!! THE CARD BATTLE — 對戰網頁

《魔法少年賈修 CCG》規則全自動裁決的同機雙人(hotseat)對戰網頁。
規則依據 [ref/raw/rule3.md](ref/raw/rule3.md),卡池為第一彈(Series 1 Level 1)全 67 種卡。

## 啟動

```bash
pip install -e ".[dev]"
uvicorn gash.api.app:app --reload
# 瀏覽器開 http://127.0.0.1:8000/
```

開頁即自動建立對局,雙方共用「賈修+蒂歐+康裘美」預組魔本(`data/decks/level1.json`)。
兩位玩家輪流操作同一畫面;畫面上方為玩家 2、下方為玩家 1,綠框標示目前該行動的一方。

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
  api/app.py            FastAPI 薄殼:對局管理、指令轉發、狀態快照(隱藏未翻頁)
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

## 架構備註(為線上化預留)

- 後端為權威伺服器:規則、隨機數、狀態全在引擎;前端只渲染快照與送指令。
- 事件流帶全域序號,支援 `GET /api/games/{id}/events?since=N` 增量同步。
- 狀態快照不包含魔本未翻開頁面的內容(防偷看,也是線上化的正確資訊邊界)。
- hotseat 模式指令帶 `player` 欄位且伺服器信任之;線上化時改由連線身分決定,引擎介面不變。

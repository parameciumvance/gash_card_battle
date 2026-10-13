## Context

- 抓取:`tools/scrape_ja_effects.py <產品頁…>` 依「収録カード」清單逐卡抓取,資料頭 token 封閉分類,未知即 raise;已存在的卡號跳過。
- 轉換:`tools/build_cards_json.py` 由 CSV 產生 `cards.json`,`image_url` 取自 TTS 卡表 A 欄超連結,`sets` 沿用舊值。
- 卡片文字:`tools/build_card_texts.py` 產生 `cards.ja.json`、寫入 `cards.en.json` 的 name/attr(effect 手寫保留);`cards.zh-TW.json` 手寫;`build_zh_cn.py` 產生簡中。
- 構築規則:引擎 `validate_deck`(建房、加入、NPC 牌組、預組),前端 `validateDeckPages`(即時提示)。

## Goals / Non-Goals

**Goals:** 第三彈 102 張的完整資料與四語文字;未實作的卡不能使用。

**Non-Goals:** 任何卡片效果(之後分批的 change);第三彈預組;規則頁的新機制說明;「土」元素的規則意義(盤點新機制時再確認)。

## Decisions

### D1:抓取工具

- `ELEMENT_TOKENS` 加「土」。
- 「ダメージ?」:`damage` 欄存「?」。
- `--range M-032:M-053`(可重複):只抓範圍內的卡號;未指定時行為不變。
- 四個商品頁:LEVEL:3(pages/35)、ガッシュ・ベルと仲間達(pages/1189)、ゼオンと最凶魔物達(pages/1190)、魔本ファイル(pages/58,限 `M-032:M-034`)。

### D2:轉換

- `damage == "?"` → `damage: null`、`damage_variable: true`(其他卡不輸出此鍵)。`CardDef` 加 `damage_variable: bool = False`。
- `sets`:沒有舊值時取 xlsx Sets 欄(`, ` 分隔)。

### D3:尚未開放的卡

- `data/pending_cards.json`:`{"_comment": …, "cards": [卡號…]}`。引擎 `pending_cards()` 讀取(快取);`validate_deck` 在卡號存在檢查之後拒絕 `deck.card_pending`。
- 前端啟動時讀 `/data/pending_cards.json`(與 `cards.json` 同一個靜態路徑),`renderCardPool` 與產品清單排除;`validateDeckPages` 加 `deck.err.pending`。
- 以清單而非卡片欄位:轉換工具每次重新產生 `cards.json`,欄位會被覆蓋;清單由實作的 change 維護,改動明確。

### D4:文字

- 英文卡名 / 屬性:`build_card_texts.py` 自 TTS 卡表寫入(既有流程)。英文效果文、繁中卡名與效果文:依 `effect_ja` 起草。「」括起的卡名改成該語言的卡名;繁中譯名沿用既有慣例(角色名、戰術名與已收錄卡一致)。
- 繁中效果文沿用既有寫法:造成傷害的戰鬥戰術冠「以攻擊方獲勝時,」、「魔力勝負で勝ったとき、相手の攻撃を無効」寫「以防禦方獲勝時,將對手的攻擊無效」、「勝敗にかかわらず」寫「無論魔力勝負結果」、「魔本を見る」寫「檢視」、「めくる」寫「翻…頁」、事件卡使用條件寫「此事件卡僅於…時可使用」;搭檔的效果名帶《》(同 P-001)。英文沿用 "Power showdown"、"takes damage"。
- 卡面:`damage_variable` 時資訊列顯示「傷害 ?」(`ui.damage` 的數值帶「?」)。

## Risks / Trade-offs

- [AI 起草的翻譯有誤] → 只影響顯示,標為初版待校對;遊戲行為以日文效果文為準。
- [卡圖下載失敗] → 前端以文字卡面呈現;失敗清單重試。M-050 的 Drive 連結非公開(轉到登入頁),目前沒有卡圖。
- [清單忘了移除] → 實作 change 的 tasks 都要包含「自清單移除」。

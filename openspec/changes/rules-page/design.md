## Context

- 規則來源:`ref/raw/rule3.md`(規則書中譯,開發參考;被 .gitignore 排除)。行為的權威是 `game-engine` 規格與引擎實作;規則頁是給玩家讀的說明。
- 卡池為第一、二彈。進階規則中實作的有:最後一頁的術(費用 0)、魔物消失處理、負傷。石版、W / VS / S / H 魔物、MJ12、巴爾肯、飛行狀態都不在卡池。
- 卡圖(`frontend/assets/cards/`)是英文版掃描,由玩家另外安裝,不進 repo。圖示可辨識:
  - 右上:費用、A(攻)、D(防)。
  - NO BATTLE(非戰鬥)。
  - 效果文左側:BATTLE(戰鬥)、CUT-IN(ジャマー)。
  - 左下:魔力。
  - 右下:傷害。
- 「攻(A)」「防(D)」的意思依卡片而不同(規則書):
  - 攻防用的術:攻擊 / 防禦時使用。
  - 事件卡、非戰鬥術:自己是 / 不是回合玩家時使用。

## Goals / Non-Goals

**Goals:**

- 新手在遊戲內就能查到規則,用語和畫面、卡面一致。
- 從當下的時機或提示一鍵跳到對應說明。

**Non-Goals:**

- 逐步教學(todo「教學」另案;可引用本頁段落)。
- 逐卡說明(卡片效果由放大檢視提供)。
- 其他語言(結構支援,內容只寫中文)。

## Decisions

### D1:內容檔的結構

`frontend/i18n/rules.zh-TW.json`:

```text
{
  "title": "...",
  "sections": [
    {"id": "goal", "title": "...", "blocks": [
        {"p": "段落文字"},
        {"list": ["條列", ...]},
        {"figure": "anatomy"},          ← 由程式繪製的範例卡標示
        {"icons": true}                 ← 由程式繪製的圖示對照
    ]},
    ...
  ]
}
```

- 渲染一律用 DOM(textContent),不拼 HTML。
- 段落以 `id` 連結。
- 範例卡標示與圖示裁切的座標放在程式(`RULE_FIGURES`),因為那是版面資料;文字說明仍在內容檔與 i18n。

### D2:段落與連結

段落 id(暫定):`goal`、`cards`、`icons`、`setup`、`turn`、`actions`、`battle`、`damage`、`effects`、`coins`、`advanced`。

對應:

```text
時機指示   start → turn          nonbattle → actions
           battle_in / defense / effects → battle      end → advanced(魔物消失處理)
行動欄提示  hint.play / field_effect / *_cards / pass_end → actions
           hint.attack / allow_battle / insert_action / defend / no_defense / battle_effects / pass_showdown → battle
           hint.start → turn    hint.deploy → advanced    hint.pending → (無連結)
```

對應表放在 `app.js`;測試檢查表中每個 id 都存在於內容檔。

### D3:範例卡標示與圖示裁切(執行時,用已安裝的卡圖)

- **範例卡**:M-001(類型、魔力、BATTLE)、S-001(費用、A、D、術魔力、傷害)、S-026(NO BATTLE)、M-026(CUT-IN)。
  - 卡圖以 `<img>` 顯示。
  - 標記以百分比座標絕對定位(卡圖等比例縮放時位置不變)。
  - 圖說用編號對應。
- **圖示對照**:以 `background-image` 指向範例卡,用百分比的 `background-size` / `background-position` 裁出單一圖示。
- **缺圖時的替代**:先以 `Image` 載入範例卡,失敗則整節改用文字標籤(例如「A」「NO BATTLE」)並顯示「卡圖未安裝」提示。
- 不在 repo 新增任何由卡圖衍生的圖檔,維持卡圖外部化的做法。

### D4:入口與覆蓋層

- 規則頁是獨立的覆蓋層(`#rules-overlay`),z-index 介於資訊對話框與聚焦之間;開啟時不暫停任何東西,只是蓋在畫面上。
- 首頁新增入口;頂欄新增「規則」按鈕(對局內外都可用)。
- `openRules(sectionId)`:開啟後捲動到段落,目錄標示目前段落。
- 時機指示的步驟、詳細提示每一條的「?」都呼叫 `openRules`。

### D5:提示用語

- `hint.own_turn_cards` / `hint.opp_turn_cards` 改為「使用帶『攻(A)』/『防(D)』圖示的事件卡或非戰鬥術」。
- `hint.attack`、`hint.insert_action`、`hint.defend` 同步改為「攻(A)」「防(D)」。
- `hint.battle_effects` 改為「BATTLE」圖示,和卡面一致。

### D7:實作中的調整

- **範例卡的標記改為框線**:原本把編號圓點放在圖示中心,會把圖示本身蓋住;改為在圖示外圍畫框、編號放在框的左上角。
- **單一位置表**:範例卡標記與圖示對照共用 `ART_BOXES`(每個圖示一個像素框),換卡圖版本時只需調整一處。
- **規則內容的載入時機**:`RULES` 在 `boot` 中於卡片資料之後載入,首頁入口與頂欄按鈕在那之後才可用;測試等 `RULES` 載入完成再操作。

### D6:驗證

- 內容檔不得出現不存在的機制:測試掃描關鍵字(石版、W魔物、VS魔物、S魔物、H魔物、MJ12、巴爾肯、飛行)。
- 連結完整:時機指示與提示的對應表、內容檔中的段落 id 都存在。
- 瀏覽器測試:
  - 頂欄開啟 / 關閉不影響對局。
  - 跳到段落。
  - 缺圖時的文字替代(以不存在的卡圖路徑模擬)。

## Risks / Trade-offs

- [規則頁與引擎行為不一致] → 內容依 `game-engine` 規格撰寫,歸檔前逐節對照;規格改動時(如新增機制)要同步更新規則頁,寫進 `battle-ui/design.md` 提醒。
- [範例卡的圖示位置因卡圖版本不同而偏移] → 座標以百分比、針對固定的範例卡;換卡圖版本時調整 `RULE_FIGURES` 即可。

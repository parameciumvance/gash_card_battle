## Context

- 介面文字已集中在 `frontend/i18n/zh-TW.json`(397 條),經 `t(key, params)` 取用;程式中寫死的顯示文字只剩「(你)」。行動記錄由前端依事件組成,伺服器不送文字(錯誤訊息除外)。
- 卡片文字由 `ZH`(`data/cards.zh-TW.json`)提供,欄位為 `name`、`name_ja`、`attr`、`effect`;`cname()` 對魔物以「名稱《效果名》」區分同名魔物(ガッシュ・ベル、ブラゴ、キャンチョメ、ティオ 共 13 張)。
- 日文來源:`data/cards_ja.csv`(權威)。魔物與夥伴的效果名不在 `attr_ja`,而是在 `effect_ja` 中以《》括起(如 M-001「《やさしい王様》MPを1へらす→…」)。
- 英文來源:`openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 有全部 135 張的英文卡名與 Attribute / Effect Name,以及英文效果文。玩家另外安裝的卡圖是民間英譯版(卡面印有「Zatch Bell! The Card Battle Scanlation Project」)。卡表與卡圖的英文效果文與日文效果文有出入(見 AGENTS.md 與 `2026-09-28-effect-tree-migration` design 第 4 節)。
- 錯誤:伺服器以 `{code, message}` 回應,`message` 是中文;前端目前直接顯示 `message`。伺服器程式中共約 88 種錯誤碼(`IllegalCommand`、`DeckError`、`RoomError`、`HTTPException` 的 `code`)。
- `GET /api/decks` 在伺服器端以中文字典解析 `name_key`;目前字典裡沒有 `deck.level1` / `deck.level2`,實際顯示的是牌組 JSON 內嵌的 `name`。
- 建立瀏覽器的測試只有 6 處(`new_context`),多數測試比對中文字串。

## Goals / Non-Goals

**Goals:**

- 日文、英文使用者不需看懂中文就能從首頁一路玩到對局結束。
- 同一房間的玩家各自使用自己的語言。
- 語言內容的一致性(條目、參數、段落、卡片涵蓋)由測試保證,翻譯品質之後可逐步修正。

**Non-Goals:**

- 母語者校對(日、英為初版翻譯,之後再修)。
- README、規格文件、伺服器 log 的多語化。
- 伺服器端錯誤訊息改寫(前端依錯誤碼翻譯即可)。

## Decisions

### D1:語言清單與偵測

- 語言清單放在 `frontend/i18n/languages.json`:`[{code, name}]`,`name` 為各語言自己的稱呼(中文 / English / 日本語)。清單順序即選單順序;新增語言時登記在這裡。
- 目前語言存在 localStorage `gash-lang`。沒有記錄時依 `navigator.languages` 逐一比對:第一個以 `ja` 開頭者為 `ja`,以 `zh` 開頭者為 `zh-TW`;都不符合時為 `en`。只看「第一個能對應的」偏好,所以「fr, ja」的瀏覽器會得到日文。
- 不採「一律中文」:看不懂中文的人第一眼就要能用。

### D2:依語言載入

`boot()` 依目前語言載入 `i18n/{lang}.json`、`i18n/rules.{lang}.json`、`/data/cards.{lang}.json`,取代目前寫死的 `zh-TW`。卡片文字的全域變數 `ZH` 改名為 `TEXT`(意思不再是中文)。目前語言的檔案載入失敗時退回 `zh-TW`,不讓頁面空白。

`<html lang>` 設為目前語言;CSS 依 `:lang(ja)` 把字型換成日文字型(`"Noto Sans JP", "Hiragino Sans", "Yu Gothic", "Meiryo", sans-serif`),避免漢字以中文字形顯示。

### D3:語言按鈕與切換

- 頂欄新增 `#lang-toggle`,顯示「🌐 + 目前語言的稱呼」,所有畫面都顯示。點擊開啟與「演出」相同形式的資訊對話框,列出語言清單的各項(以各自的語言標示),目前語言標為已選。
- 選擇後寫入 `gash-lang` 並 `location.reload()`。
  - 重新載入走既有的接回路徑:對局(`?room=`,token 存在本機)、觀戰、構築器(`?builder=1`)、加入連結(`?join=`)都會回到原處;行動記錄由伺服器補回全部事件,以新語言重建。
  - 設定頁不在網址中,重新載入後回到首頁(選擇已被記住)。
- 不採「就地重繪」:需要讓每個已渲染的元件(行動記錄、對話框、聚焦展示、構築器)都能重建,容易漏;重新載入一次就全部正確,而且接回路徑已有測試。

### D4:卡片文字檔

- **`cards.ja.json`**:新增 `tools/build_card_texts.py` 由 `data/cards_ja.csv` 產生。`name` / `name_ja` = `name_ja`;`effect` = `effect_ja`;`attr`:術卡為 `attr_ja`,魔物與夥伴卡為 `effect_ja` 中第一個《》內的文字,沒有時 null;事件卡 null。測試以同一函式重新產生並比對,檔案不得手動修改。
- **`cards.en.json`**:`name`、`attr` 取自 TTS 卡表(同一工具產生並寫入,保留檔中既有的 `effect`);`effect` 依 `effect_ja` 逐卡翻譯(手寫,存於檔中)。翻譯時:
  - 用語對齊卡圖:MAMODO、SPELL、Spell Book、Power、MP、Partner、【STANDBY】、【STAY】、BATTLE、CUT-IN。
  - 「」括起的卡名 / 術名改為該卡的英文 `name`,保留引號,讓玩家能對到卡片。
  - 卡表的英文效果文只作用語參考,不作翻譯依據。
- 測試:兩個檔都涵蓋 `cards.json` 全部卡號;`name_ja` 與 `cards_ja.csv` 一致;英文 `name` / `attr` 與卡表一致;英文 `effect` 非空且不含日文假名(避免漏翻)。

### D5:卡名的呈現

- 同名魔物的區分格式放進字典:`ui.card_with_attr`(中文、日文「{name}《{attr}》」,英文「{name} ({attr})」)。
- 卡名下方的小字:目前語言不是日文時顯示 `name_ja`;日文時不顯示(與卡名重複)。

### D6:錯誤碼

- 前端 `api()` 失敗時,若字典有 `error.<code>` 就以它為訊息,否則用伺服器的 `message`。
- 三種語言的字典為每個錯誤碼提供一條**通用**訊息,不帶伺服器訊息中的動態參數(如卡號);同一錯誤碼在伺服器有多種文字時,取其共同意思。
- 測試掃描伺服器程式中的錯誤碼(`IllegalCommand("…"`、`DeckError("…"`、`RoomError(…"…"`、`"code": "…"`、`_npc_http_error("…"` 等),要求三種字典都有 `error.<code>`。新增錯誤碼時測試會提醒補翻譯。

### D7:預組名稱

`GET /api/decks` 每項多回傳 `name_key`(有時)。前端顯示預組名稱時,若目前字典有 `name_key` 就用它,否則用 `name`。三種字典補上 `deck.level1`、`deck.level2`;伺服器端仍以中文字典解析 `name`,作為備用。

### D8:用語

- **日文**:規則書用語,如スタートフェイズ、バトルフェイズ、エンドフェイズ、ターンプレイヤー、魔本、術、魔物、パートナー、イベント、魔力、ダメージ、負傷状態、かばう、スタンバイ、ステイ、ジャマー、捨て札、表 / 裏。卡面圖示仍稱「攻(A)」「防(D)」「BATTLE」「NO BATTLE」「CUT-IN」(卡圖上印的是英文與漢字)。
- **英文**:對齊卡表與卡圖的寫法(以卡表英文效果文的出現次數為準),如 START PHASE、BATTLE PHASE、END PHASE、turn player、Spell Book、SPELL、MAMODO、Partner、Event、Power、damage、Injured、PROTECT、STANDBY、STAY、Discard Pile、heads / tails;圖示稱「A (Attack)」「D (Defense)」「BATTLE」「NO BATTLE」「CUT-IN」。
- 規則頁不存在機制的檢查,依語言檢查對應稱呼(日文:石版、W魔物、VS魔物、S魔物、H魔物、MJ12、バルカン、飛行;英文:Stone Tablet、W Mamodo、VS Mamodo、S Mamodo、H Mamodo、MJ12、Vulcan、flying)。

### D9:測試

- 6 處 `new_context` 加上 `locale="zh-TW"`:既有測試維持中文,同時驗證了「依瀏覽器語言」的路徑。
- 靜態測試:三種字典條目與參數一致;規則頁三種語言段落 id 與順序一致、不提不存在的機制;卡片文字檔(D4);錯誤碼(D6)。
- 瀏覽器測試:依瀏覽器語言決定預設(ja、fr → en);選擇後記住;對局中切換後接回且記錄為新語言;同房兩位玩家不同語言;錯誤訊息依語言;預組名稱依語言;日文卡名與小字。

### D10:實作中補充的決定

- **放大檢視的卡名**:放大檢視以 `cname()`(含效果名,如「ガッシュ・ベル《やさしい王様》」「Zatch Bell (Kind King)」)顯示卡名;盤面等小卡仍只顯示卡名(版面有限)。中文的放大檢視因此也會顯示效果名。
- **分隔符號與括號進字典**:原本寫死在程式中的「、」「・」「|」「(…)」「玩家:標題」改為 `ui.sep.list`、`ui.sep.meta`、`ui.sep.bar`、`ui.paren`、`ui.choice_title`,英文用「, 」「 · 」「 | 」等;「(你)」改為 `ui.you_suffix`。
- **英文卡片效果文不含開頭的《效果名》**:日文效果文開頭有《效果名》,英文與中文一樣省略(效果名已在卡名中呈現),效果名之前的文字(如「自分の「ゴフレ」に重ねる。」)照譯。
- **預組名稱**:兩副預組都用商品名(專案負責人決定;日文原名見 atwiki「カードリスト」頁)。LEVEL:1:中「LEVEL:1 紅書與魔鬼」、日「LEVEL:1 赤い本と魔物の子」、英「LEVEL:1 The Red Book and the Mamodo Child」;LEVEL:2:中「LEVEL:2 來自黑色魔界的使者」、日「LEVEL:2 黒き魔界よりの使者」、英「LEVEL:2 Messenger from the Dark Mamodo World」。英文暫時自日文翻譯。牌組 JSON 內嵌的 `name` 同中文名稱,作為字典沒有時的備用。
- **手機時機指示**:英文的時機指示用較短的標籤(No BATTLE、BATTLE:、Check),維持手機單行;頂欄按鈕不換行,避免日文按鈕被擠成直排。
- **語言偵測的比對方式**:以主語言(`-` 前的部分)比對語言清單,`zh-CN`、`zh-HK` 等也歸為中文(目前只有繁體中文)。

## Risks / Trade-offs

- [翻譯品質] 日、英為初版,用語或語氣可能不自然 → README 與本 design 註明「初版翻譯,尚未經母語者校對」;結構測試只保證完整與一致。
- [英文效果文與卡圖不同] 英文效果依日文翻譯,會與玩家卡圖上的英文不完全相同 → 這是刻意的:遊戲行為依日文效果文,畫面文字應與行為一致;規則頁與 README 說明以畫面文字為準。
- [英文字串較長] 手機版面可能擠 → 實作後截圖檢查首頁、設定頁、對局、行動欄、對話框;盤面卡名本來就限兩行省略。
- [切換時重新載入] 設定頁中切換會回到首頁 → 選擇已被記住,影響小。
- [新增錯誤碼忘了翻] → D6 的測試會失敗。

## Migration Plan

純前端與資料新增,`/api/decks` 只多一個欄位。既有使用者沒有 `gash-lang`,第一次開啟會依瀏覽器語言決定;中文瀏覽器使用者看到的與現在相同。

## Context

- 玩家多半沒有 GitHub 帳號,所以主要管道放在不需要登入的地方。
- 遊戲分兩種部署:VPS 和玩家電腦上的單機版。回報管道必須兩邊都能用,而且不能在前端放任何秘密。
- 要重現卡片效果的問題,最需要的是當下的模式、房號、回合與階段。

## Goals / Non-Goals

**Goals:**

- 不用帳號就能回報,入口在首頁與對局中都找得到。
- 自動帶上足以定位問題的環境資訊,不需要玩家自己描述。

**Non-Goals:**

- 遊戲內直接送出、附上完整對局記錄(方案 B,列入 todo)。
- 伺服器端儲存或轉發回報。

## Decisions

### D1:設定放在前端常數 `FEEDBACK`

`app.js` 開頭:

```text
FEEDBACK = {
  formUrl:      Google 表單的 viewform 網址；空字串時不顯示表單管道
  contextEntry: 表單「環境資訊」欄位的 entry id(例如 "entry.123456")；空字串時不預填
  issuesUrl:    GitHub「new issue」選擇頁
}
```

- 表單網址公開也沒關係,而且 VPS 和單機版都一樣,所以不需要放到伺服器設定。
- 表單還沒建立時(`formUrl` 空白),對話框只顯示 GitHub 管道,功能不會壞掉。

### D2:環境資訊

`feedbackContext()` 產生一行固定格式、不翻譯的文字,對象是開發者:

```text
lang=zh-TW; mode=npc; room=ABCD; turn=5; phase=battle; ua=Mozilla/5.0 ...
```

- 首頁(沒有對局)時只有 `lang` 與 `ua`。
- 不帶 token、暱稱、牌組內容。房號本身不是秘密(加入連結就是房號),而且有房號才能對照伺服器記錄。
- 預填到表單時用 `formUrl?usp=pp_url&<contextEntry>=<encodeURIComponent(文字)>`(Google 表單的預填網址格式)。
- 對話框也顯示同一份文字並提供「複製」按鈕,讓用 GitHub 的人貼上。

### D3:對話框沿用資訊對話框

使用 `showInfo("feedback", ...)`:純展示,開啟或關閉都不影響對局,和演出設定相同。外部連結用 `<a target="_blank" rel="noopener">`,在新分頁開啟,對局分頁保留。

### D4:入口位置

- 首頁:在「規則」之後新增「意見回報」入口。
- 頂欄:在「規則」旁新增「回報」按鈕,對局內外都可以用；回報通常發生在對局中。

### D5:GitHub Issue Forms

- `bug.yml`(問題回報)、`card-effect.yml`(卡片效果不符:卡號、預期依據的效果文、實際行為)、`suggestion.yml`(建議)。
- 每個範本都有 `environment` 欄位,說明可以從遊戲內「回報」對話框複製。
- `config.yml` 保留空白 issue,並以 `contact_links` 連到 Google 表單(表單建立後再補上)。

## Risks / Trade-offs

- [Google 表單的檔案上傳題需要 Google 登入] → 表單不使用上傳題,改請玩家貼圖片連結,或改用 GitHub。README 寫明表單的建議題目。
- [回報散在 Google 試算表] → 維護者自行整理成 issue；方案 B 會解決這個問題。

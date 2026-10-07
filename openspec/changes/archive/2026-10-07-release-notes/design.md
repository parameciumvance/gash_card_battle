## Context

- 給玩家看的多語長文目前只有規則頁:`frontend/i18n/rules.<lang>.json`,繁中手寫、簡中由 `tools/build_zh_cn.py` 轉換、英日另寫,`tests/test_i18n_languages.py` 檢查各語言段落一致;前端以 `fetchJson` 依 `LANG` 載入,失敗時改用繁中。
- 首頁免責聲明下方已顯示版本號(`#landing-version`,取自 `GET /api/meta`,由 tag 經 build arg 帶入)。
- 發布:推送 `v*` tag → `deploy.yml` 建置映像檔並推上 GHCR → VPS 的 watchtower 更新。映像檔不含 `tools/`。目前不建立 GitHub Release。
- 動機見 proposal.md「Why」。

## Goals / Non-Goals

**Goals:** 單一來源(repo 內的資料檔)同時供網頁與 GitHub Release 使用;漏寫某版或漏翻某語言時,在測試或 CI 就失敗。

**Non-Goals:** 不由 commit 訊息自動產生(commit 寫給開發者看);不在伺服器端記錄玩家看過哪一版;GitHub Release 不放多語。

## Decisions

### D1:資料檔與 rules 同一套模式

`frontend/i18n/releases.<lang>.json`:

```json
{
  "releases": [
    { "version": "v0.9.3", "date": "2026-10-06",
      "items": [ { "kind": "change", "text": "圖片顯示速度優化" } ] },
    { "version": "v0.9.2", "date": "2026-10-06", "title": "公開上線", "items": [] }
  ]
}
```

- 陣列順序即顯示順序,最新的在第一個;「最新一版」= 第一個元素。
- `title` 可省略;`items` 可為空陣列。`kind` 為 `new` / `fix` / `change`,標籤走 i18n 字典(`release.kind.<kind>`)。
- 文字為純文字,以 DOM 建構呈現,不解析標記。
- 替代方案:單一檔案、每個條目內含各語言(`{"zh-TW": …, "en": …}`)。翻譯放在一起較好對照,但與既有 rules / 簡中轉換工具的檔案模式不同,前端也要載入全部語言。採用與 rules 相同的模式。
- 放在 `frontend/i18n/` 而非 `data/`:與 rules 一樣是前端顯示用的多語文字,靜態檔路由與快取規則(`no-cache`)已涵蓋。

### D2:各語言一致性由測試保證

`tests/test_i18n_languages.py` 加入檢查:四種語言的版本、日期、`title` 有無、條目數與各條目 `kind` 完全相同;版本號符合 `vX.Y.Z` 且由新到舊排列、不重複;文字非空。漏翻在一般 push 的測試就會失敗。

簡中由 `tools/build_zh_cn.py` 轉換(加入 `FILES`);`version`、`date`、`kind` 是 ASCII,不受轉換影響,不必列入 `SKIP_KEYS`。

### D3:首頁跳出與記錄

- localStorage `gash-release-seen` 存玩家按過「確認」的版本號。進入首頁(`show("landing")`)時,若最新一版的版本號 ≠ 記錄值,且本次載入尚未跳出過,就跳出最新一版。
- 只比較「是否等於最新一版」,不比大小:記錄值是舊版、不存在、或格式不明,都一律跳出。不必解析版本號。
- 按「確認」才寫入;Esc 或其他關閉方式不寫入,只設本次載入的旗標避免同一次載入內重複跳出。localStorage 無法存取時讀到 null,視為未確認。
- 只掛在進入首頁的路徑上:房號連結、觀戰、重連直接進入的畫面不經過首頁,自然不跳出;離開房間回到首頁時才判斷。
- 版本號與入口放在免責聲明的 `<footer>` 之外(同一個外層容器):既有規格要求免責聲明本身不是按鈕或入口,也不含按鈕。
- 面板沿用規則頁 / 資訊面板的樣式。跳出時只有最新一版與「確認」;「更新內容」入口開的是全部歷史,只有「關閉」。
- 更新內容在首頁渲染時才需要:啟動時與 rules 一起載入(檔案小),目前語言載入失敗改用繁中;都失敗時不跳出、入口隱藏。

### D4:發布工具與 CI

新增 `tools/release_notes.py`(CI 用,讀 `releases.zh-TW.json`):

- `check <tag>`:最新一版的版本號必須等於 tag,否則以非零結束並印出缺少的版本。要求「最新一版 = tag」而非「存在該版」:發布時新條目一定在最前面,也避免 tag 打錯舊版號時誤過。
- `markdown <tag>`:輸出該版的 GitHub Release 內容(標題、`[分類] 條目` 清單,分類用繁中標籤)。

`deploy.yml`:checkout 後先跑 `check`,失敗則不建置;建置推送後以 `markdown` 的輸出建立 GitHub Release(`gh release create`,工作需 `permissions: contents: write`)。工具只用標準函式庫,CI 不必安裝專案依賴。

替代方案:在 `test.yml` 檢查。一般 push 時還沒有 tag,無從比對;放在 deploy 才能對應到實際發布的版本。

### D5:補寫的版本

- v0.9.3(2026-10-06):`[調整] 圖片顯示速度優化`(卡圖改 WebP)。
- v0.9.2(2026-10-06):標題「公開上線」,無條目。
- v0.9.0、v0.9.1 不列出。
- 英文與日文由 Agent 依繁中起草,使用者審閱。

## Risks / Trade-offs

- [發布前忘了寫更新內容] → CI 擋下不建置,線上維持舊版;補上條目後刪除並重推 tag。README 的發布步驟寫明順序。
- [英日翻譯品質] → Agent 起草、使用者審閱後才 commit;測試只保證結構一致,不保證譯文。
- [跳出面板打擾玩家] → 只在首頁、每版確認一次;新玩家也會看到最新一版,屬於預期(作為功能介紹)。
- [GitHub Release 建立失敗(權限、網路)] → 映像檔已推送、服務照常更新;Release 可事後以工具輸出手動建立。建立 Release 放在推送之後,不影響部署。

## Migration Plan

1. 實作並 push 到主分支:只跑測試,不部署;開發環境中最新一版是 v0.9.3。
2. 下一次發布前,在三個手寫語言檔最前面加入新版本(涵蓋音效、手機排版等尚未發布的修改),產生簡中,commit 後再打 tag。上線後所有玩家(含現有玩家)在首頁看到這一版的介紹一次。
3. 回退:移除 deploy.yml 的檢查與 Release 步驟即可恢復舊流程;前端資料檔不影響其他功能。

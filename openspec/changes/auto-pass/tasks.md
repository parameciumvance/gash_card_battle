# Tasks

## 1. 可用行動的判斷與快照

- [x] 1.1 先寫測試(確認修改前失敗):非戰鬥中非回合玩家沒有可用行動 → `idle.auto` 為 pass;有可用的場上效果 → `has_actions`;戰鬥開始確認有可用事件卡 → `has_actions`,沒有 → `auto` 為進入戰鬥;防禦步驟只有魔物效果防禦 → `has_actions`,沒有任何防禦 → `auto` 為不防禦;效果步驟;回合玩家、對手、觀戰者、有 pending 時沒有 `idle`;判斷不改變實際狀態
- [x] 1.2 實作 D1。1.1 通過

## 2. 前端

- [ ] 2.1 瀏覽器測試先寫:開關預設勾選、觀戰者不顯示、重新整理後保留;`idle.auto` 時約 2 秒自動送出一次;放大檢視開著時不送、關閉後再 2 秒;自己先按只送一次;關掉開關不送;`has_actions` 時顯示提示且不送
- [ ] 2.2 實作 D2、D3(四語)。2.1 通過;行動欄相關的既有瀏覽器測試照舊(既有測試若受自動 pass 影響,在測試中關閉開關,不改變原本要驗證的行為)

## 3. 驗證與文件

- [ ] 3.1 快速測試組與相關瀏覽器測試通過;battle-api、battle-ui design 補 D1–D3;`openspec validate auto-pass --strict`
- [ ] 3.2 本機實際操作抽查(使用者)

## Workflow follow-up

- 歸檔前同步 battle-api、battle-ui delta spec 與 design;在 `auto-pass` 分支歸檔提交,合併回 `dev`。

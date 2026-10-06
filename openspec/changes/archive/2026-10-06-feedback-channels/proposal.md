## Why

玩家目前沒有管道回報問題或提供意見。repo 的 GitHub issue 需要帳號,介面也偏工程師,一般玩家很少會用。卡片效果的問題如果缺少當時的對局資訊,也很難重現。

## What Changes

- **意見回報入口**:首頁新增「意見回報」入口,對局頂欄新增「回報」按鈕,兩者開啟同一個對話框。對話框提供兩個管道:
  - Google 表單(不需登入,主要管道):連結預先帶入環境資訊(語言、模式、房號、回合、階段、瀏覽器)。
  - GitHub issue(需要 GitHub 帳號)。
  - 對話框也顯示同一份環境資訊並可複製,方便貼到 GitHub issue。
- **GitHub Issue Forms**:新增 `.github/ISSUE_TEMPLATE/`,包含問題回報、卡片效果不符、功能建議三種範本,並在選擇頁附上 Google 表單連結。
- **TODO**:遊戲內直接送出回報、自動附上對局記錄(方案 B),列入 `openspec/changes/todo.md`,這次不做。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:修改「首頁入口」(新增意見回報入口)；新增「意見回報」。

## Impact

- 前端:`frontend/index.html`、`app.js`(`FEEDBACK` 設定、對話框、環境資訊)、`style.css`、三種語言的 `i18n/*.json`。
- Repo:`.github/ISSUE_TEMPLATE/*.yml`、README。
- 伺服器與引擎不變。

## 1. 先寫測試

- [x] 1.1 瀏覽器測試:首頁入口多了「意見回報」；首頁與頂欄都能開啟對話框；表單連結帶預填環境資訊；未設定表單時只顯示 GitHub；對局中的環境資訊含模式、房號、回合；開關不影響對局。確認修改前失敗
- [x] 1.2 靜態測試:Issue Forms 範本是合法 YAML、都有 `environment` 欄位

## 2. 實作

- [x] 2.1 `FEEDBACK` 設定、`feedbackContext()`、`openFeedback()` 對話框(design D1–D3)
- [x] 2.2 首頁入口與頂欄按鈕(design D4),三種語言的 i18n
- [x] 2.3 `.github/ISSUE_TEMPLATE/`(design D5)
- [x] 2.4 README:回報管道與 Google 表單的設定方式
- [x] 2.5 `openspec/changes/todo.md` 加入方案 B
- [x] 2.6 截圖確認桌面與手機

## 3. 待使用者

- [x] 3.1 建立 Google 表單,填入 `FEEDBACK.formUrl`、`contextEntry`,並補上 `config.yml` 的 `contact_links`

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補意見回報(設定位置、環境資訊格式與不帶的資料)
- [x] 4.3 Update capability map(`battle-ui` 責任補上意見回報)
- [x] 4.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

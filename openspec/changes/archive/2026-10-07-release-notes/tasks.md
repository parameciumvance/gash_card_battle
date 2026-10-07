## 1. 更新內容資料與語言一致性

- [x] 1.1 `tests/test_i18n_languages.py` 加入更新內容的一致性檢查(design D2:四種語言的版本、日期、標題有無、條目數與分類相同;版本號格式、由新到舊、不重複;文字非空),先確認在沒有資料檔時失敗
- [x] 1.2 建立 `frontend/i18n/releases.zh-TW.json`,補寫 v0.9.3 與 v0.9.2(design D5)
- [x] 1.3 起草 `releases.en.json`、`releases.ja.json`,使用者已審閱
- [x] 1.4 `tools/build_zh_cn.py` 加入 releases,產生 `releases.zh-CN.json`;1.1 的測試通過

## 2. 首頁跳出與更新內容面板

- [x] 2.1 瀏覽器測試(battle-ui「更新內容」各情境):首次跳出最新一版且條目帶分類;按確認後重新整理不再跳出;最新一版改變後再次跳出;未確認關閉時同次載入不重複、重新整理後再跳;經房號連結進入對局不跳出、回到首頁才跳;只有標題的版本無條目清單;入口列出全部版本由新到舊;日文顯示。確認修改前失敗
- [x] 2.2 i18n 字典(四種語言):入口、面板標題、確認、關閉、`release.kind.new|fix|change`;`test_i18n_languages` 通過
- [x] 2.3 `app.js` / `index.html` / `style.css`:啟動時載入更新內容(失敗改用繁中)、進入首頁時判斷跳出、`gash-release-seen` 只在確認時寫入、版本號旁的入口與全部歷史面板(design D3);2.1 的測試通過
- [x] 2.4 截圖確認桌面與手機的跳出面板與歷史面板

## 3. 發布工具與 CI

- [x] 3.1 `tools/release_notes.py`:`check <tag>`(最新一版 ≠ tag 時非零結束並指出缺少的版本)、`markdown <tag>`(輸出 GitHub Release 內容);以 `tests/test_release_notes_tool.py` 驗證成功、缺版本、tag 不是最新一版、只有標題的版本
- [x] 3.2 `deploy.yml`:建置前執行 `check`;推送後以 `markdown` 輸出建立 GitHub Release(`contents: write`)(design D4);以 YAML 解析檢查步驟順序,實際效果待下次發布確認
- [x] 3.3 README 發布步驟:先寫更新內容(三個手寫語言 + 產生簡中)並 commit,再打 tag;CI 擋下時的補救方式

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui`、`docker-deployment` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 新增「更新內容」(資料檔、跳出規則、與 rules 同一套語言模式);`docker-deployment/design.md` 的「發布與更新」補更新內容檢查與 GitHub Release
- [x] 4.3 capability map:`battle-ui` 責任補上更新內容;`docker-deployment` 補 GitHub Release
- [x] 4.4 `openspec validate --all --strict`、全部測試通過後歸檔

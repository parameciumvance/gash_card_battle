## 1. 先寫測試

- [x] 1.1 靜態測試:三個簡中檔由工具產生且與繁中同步;簡中字典與規則頁結構與繁中一致;`name_ja` 未轉換;術語表的保留與替換生效(宣告、進階規則、默认);語言清單。確認修改前失敗
- [x] 1.2 瀏覽器測試:`zh-CN` / `zh-SG` / `zh-Hans-*` 偵測為簡中,`zh` / `zh-HK` 為繁中;選單名稱;簡中卡片文字。確認修改前失敗

## 2. 實作

- [x] 2.1 `tools/build_zh_cn.py`(design D1、D2、D3),dev 依賴加上 `opencc-python-reimplemented`
- [x] 2.2 產生三個簡中檔,檢查轉換結果
- [x] 2.3 `languages.json`、`detectLang()`(design D4、D5)
- [x] 2.4 README:「翻譯校對」說明簡中由工具產生
- [x] 2.5 截圖確認簡中的首頁、對局、規則頁

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui`、`card-data` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md`「語言」(四種語言、偵測、翻譯狀態)、`card-data/design.md`「卡片文字檔」(簡中由工具產生、術語表)
- [x] 3.3 Update capability map(`battle-ui` 的語言描述)
- [x] 3.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

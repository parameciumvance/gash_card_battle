# Tasks

## 1. 測試

- [ ] 1.1 先改 / 寫瀏覽器測試並確認在修改前失敗:5 顆類型徽章(「其他」只列 MJ12、缺圖為「他」);標籤多選(干擾、中級 / 上級、屬性;網格不收起、摘要、「全部」清除、與類型複合);排序(MJ-006 後接 Ex 依編號、再 PR)。

## 2. 實作

- [ ] 2.1 「其他」類型(design D1)。
- [ ] 2.2 標籤篩選與四語文字(design D2)。
- [ ] 2.3 排序(design D3)。

## 3. 驗證與文件

- [ ] 3.1 截圖確認桌面與手機的篩選列;快速測試組與卡池、金手指相關的瀏覽器測試;`openspec validate pool-tags-and-order --strict`。
- [ ] 3.2 更新 `deck-builder/design.md`;todo 的「依標籤搜尋」。
- [ ] 3.3 使用者確認。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec;歸檔後以 `--no-ff` 合併回 `dev`。

# Tasks

## 1. 干擾標籤

- [x] 1.1 先寫瀏覽器測試並確認在修改前失敗:M-026 放大檢視、M-080 卡池小卡(一個標籤)、Ex-034 有「干擾」標籤;M-001 沒有;盤面卡面沒有;英文為「CUT-IN」。
- [x] 1.2 實作(design D1、D2):`cardEl` 資訊列加標籤、樣式、四語 `card.icon.jammer`(zh-CN 由 `build_zh_cn.py` 產生)。1.1 通過;確認卡池小卡不溢出。(截圖確認 M-026 小卡與放大檢視,資訊列沒有溢出)

## 2. 英文用語

- [x] 2.1 規則頁(`rules.en.json`)與 E-052、M-077 英文效果文的 jammer 改為 CUT-IN(design D3);確認英文顯示文字不再出現「Jammer」。

## 3. 驗證與文件

- [x] 3.1 快速測試組與卡面相關的瀏覽器測試;`openspec validate jammer-tag --strict`。(快速組 1661 項;新測試 7 項與卡面、規則頁、卡池相關的瀏覽器測試 61 項通過)
- [x] 3.2 更新 `battle-ui/design.md`(資訊列的標籤)。
- [ ] 3.3 使用者確認:本機看標籤樣式。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec 到主 spec(battle-ui)。
- 歸檔後以 `--no-ff` 合併回 `dev`。

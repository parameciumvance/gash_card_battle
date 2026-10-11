## 1. 實作

- [x] 1.1 先寫瀏覽器測試確認修改前失敗:疊放魔物的放大檢視列出下方的卡(由上而下)、點小卡改為純展示並有返回、返回後回到原魔物;對手的疊放魔物也列出;沒有疊放不顯示
- [x] 1.2 `renderZoom` 疊放區與返回(design D1)、CSS、i18n(簡中以工具產生);1.1 與既有瀏覽器測試全過
- [x] 1.3 使用者在瀏覽器實際操作確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 2.2 `battle-ui/design.md` 卡片元件 / 放大檢視的說明補疊放區
- [x] 2.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔

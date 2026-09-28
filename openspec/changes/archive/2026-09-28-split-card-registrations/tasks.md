## 1. 先改測試

- [x] 1.1 靜態測試改為檢查 `effects/cards/`:各檔只含該類別的卡號且依卡號排序、無 lambda / 函式定義;`effects/` 只有機制檔與 `cards/` 套件;決策種類的檢查讀取 `cards/` 下所有檔
- [x] 1.2 確認新測試在拆分前失敗

## 2. 拆分

- [x] 2.1 建立 `effects/cards/` 與四個類別檔,內容逐字搬移,各檔只匯入用到的名稱;排版規則移到 `cards/__init__.py`
- [x] 2.2 `effects/__init__.py` 改為匯入 `cards`;刪除 `tree_cards.py`
- [x] 2.3 確認登記順序與拆分前相同(比對各登記表的 key 順序),全部測試通過

## 3. 文件

- [x] 3.1 README(卡片效果的寫法、專案結構)、AGENTS.md 改為 `effects/cards/`

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`effect-tree/design.md` 的檔案分工
- [x] 4.3 Update capability map(確認無需變更:capability 的責任、關係與覆蓋程度都沒有改變)
- [x] 4.4 `openspec validate`、`python -m pytest` 全過後歸檔

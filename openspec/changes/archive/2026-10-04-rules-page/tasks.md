## 1. 先寫測試

- [x] 1.1 靜態測試:規則內容檔不出現不存在的機制;時機指示與提示的連結對應表中的段落 id 都存在於內容檔
- [x] 1.2 瀏覽器測試:`battle-ui`「規則頁」各情境、「首頁入口」的規則入口、「回合與時機指示」的連結與提示用語;確認修改前失敗

## 2. 規則內容

- [x] 2.1 `frontend/i18n/rules.zh-TW.json`:依 design D2 的段落撰寫,逐節對照 `game-engine` 規格與引擎實作(費用、翻頁、輪流、戰鬥流程、保護、勝利條件、進階規則)

## 3. 規則頁

- [x] 3.1 覆蓋層、目錄、段落渲染(DOM)、`openRules(sectionId)`;窄螢幕單欄(design D4)
- [x] 3.2 範例卡標示與圖示裁切、缺圖時的文字替代(design D3)
- [x] 3.3 入口:首頁、頂欄;時機指示的步驟與詳細提示的連結(design D2)
- [x] 3.4 提示用語改為「攻(A)」「防(D)」(design D5),i18n
- [x] 3.5 截圖確認桌面與手機

## 4. 文件

- [x] 4.1 README:移除連到不在 repo 的規則檔、卡池改為第一、二彈共 135 種、提到遊戲內的規則頁

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 5.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補規則頁(內容檔、連結對應、圖示裁切與缺圖替代、規格改動時須同步規則頁)
- [x] 5.3 Update capability map(`battle-ui` 責任補上規則頁)
- [x] 5.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

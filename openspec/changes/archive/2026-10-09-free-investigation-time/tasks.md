## 1. 首頁入口

- [x] 1.1 `tests/test_landing_ui.py`:入口順序改為 NPC 對戰、與朋友對戰、牌組構築、自由調查時間、規則、意見回報;自由調查時間的入口與設定頁標題(battle-ui「首頁入口」情境「首頁只有入口」「自由調查時間的名稱」);確認修改前失敗
- [x] 1.2 `index.html` 入口順序(design D3)
- [x] 1.3 i18n:`ui.landing.local`、`ui.landing.local_desc`(強調沒有電腦對手)、`error.room.not_local`、`error.room.not_joinable`(繁中、英、日手寫,簡中以 `tools/build_zh_cn.py` 產生;design D2);1.1 與 `test_i18n_languages` 通過
- [x] 1.4 截圖確認桌面與手機的首頁

## 2. 文件與 Reconciliation(指南 §13)

- [x] 2.1 README 的模式介紹改名、順序與首頁一致
- [x] 2.2 Reconcile affected capability design and rationale:`battle-ui/design.md`「首頁與設定頁」補顯示名稱與技術名稱的對照、改名與換位的理由
- [x] 2.3 同步 delta spec 回 `battle-ui` 主 spec(封存時)
- [x] 2.4 `openspec validate --all --strict`、全部測試通過

## 1. 測試先行

- [x] 1.1 `tests/test_i18n_languages.py`:同一日文元素在繁中、英文各一種譯名;有元素的戰術屬性不為空;S-091 的英文屬性為 Thunder;執行並確認修改前失敗

## 2. 修正

- [x] 2.1 `build_card_texts.py`:自卡表推導元素對照,補卡表缺漏的戰術英文屬性(同一元素有兩種英文時報錯);調整卡表一致性測試
- [x] 2.2 繁中 S-029 / S-030 / S-031 屬性改「雷」;重跑 `build_card_texts.py` 與 `build_zh_cn.py`
- [x] 2.4 日文沒有元素的 25 張戰術(含 S-058、指令戰術)繁中屬性改為空值;測試「沒有元素的戰術沒有屬性」修改前失敗
- [x] 2.3 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗

## 3. Reconciliation(指南 §13)

- [x] 3.1 同步 delta spec 回 `card-data` 主 spec(歸檔時)
- [x] 3.2 `card-data/design.md`「卡片文字檔」:英文屬性的補值規則、屬性譯名一致的測試;todo 移除此項

## Workflow follow-up

- 歸檔:`openspec archive spell-attr-names -y`,在 `spell-attr-names` 分支提交;合併 main 與推送等使用者指示

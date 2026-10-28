# Tasks

## 1. 規格與文件

- [x] 1.1 確認 delta 的 3 條 MODIFIED 與主 spec 的差異只有語言範圍的文字與新情境(以 `diff` 比對各區塊);`python -m pytest tests/test_i18n_languages.py -q` 通過,其中 `test_rules_have_same_sections[zh-CN]`、`test_every_error_code_is_translated[zh-CN]` 有執行
- [x] 1.2 `openspec/specs/battle-ui/spec.md` 的 Purpose「中文、英文、日文三種語言的介面」改為「繁體中文、簡體中文、英文、日文四種語言的介面」(Purpose 不經 delta,直接改);`openspec validate battle-ui --type spec --strict` 通過
- [x] 1.3 `README.md` 預組顯示名的說明「在三種語言的 i18n 字典補條目」改為在繁中、英文、日文字典補條目並重跑 `tools/build_zh_cn.py` 產生簡中;內容與 `tools/build_zh_cn.py` 的實際用法一致
- [x] 1.4 `todo.md` 移除「規則頁 spec 寫三種語言的內容檔…」一項
- [x] 1.5 `openspec validate zh-cn-generated-language-wording --strict` 通過

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui` 主 spec;`openspec validate --all --strict` 通過,且沒有新增說明過長的提示
- [x] 2.2 Reconcile `battle-ui/design.md`:規則頁一節「三種語言的內容檔段落 id、順序與 block 種類一致」改為三種撰寫語言一致、簡中由繁中產生(改繁中段落後要重跑 `build_zh_cn.py`);行為沒有改變,不新增行為決定;確認 capability map 不需更新
- [x] 2.3 以「三種語言」「中文、英文、日文」grep `openspec/specs`、`README.md`、`docs`,確認只剩情境名稱與指撰寫三種的用法
- [x] 2.4 依使用者指示歸檔並提交

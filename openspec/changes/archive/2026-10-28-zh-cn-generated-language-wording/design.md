## Context

背景見 proposal.md。目前四種語言的檔案關係:

```
撰寫:  zh-TW   en   ja
產生:  zh-CN  <-- tools/build_zh_cn.py 自 zh-TW 轉換(card-data「簡體中文卡片文字」)
```

`tests/test_i18n_languages.py` 已檢查四種語言:字典條目與參數、規則頁段落(`test_rules_have_same_sections` 含 `zh-CN`)、每個錯誤碼的翻譯,以及 `zh-CN` 檔與繁中同步(`test_zh_cn_files_are_generated_from_zh_tw`)。

## Goals / Non-Goals

**Goals:** 規格文字與實作的語言範圍一致,並寫明哪些語言是撰寫、哪一種是產生。

**Non-Goals:** 不改行為、程式、測試;不改情境名稱。

## Decisions

### 寫成「三種撰寫、一種產生」,不一律改成「四種語言」

只把「三」改成「四」,讀者會以為四個檔都要手寫、改規則頁時要改四份。實際上改內容的人只需要改三份撰寫的檔,再重跑 `build_zh_cn.py`。寫明兩者的關係,也讓「三種語言」的情境名稱維持正確(指撰寫的三種)。

錯誤碼的需求例外,寫「四種語言的字典」:它規範的是每個錯誤碼在玩家看到的每種語言都有訊息,和檔案是否手寫無關;括號再註明簡體中文由繁中產生。

替代方案:三條需求 REMOVED 再以新名稱 ADDED,以便把情境改名成「四種語言…」。改動大、需求名稱又要再換一次,而寫法調整後舊名稱仍然成立,不採用。

### 新情境只寫已有測試的部分

「簡體中文規則頁段落一致」只斷言段落 id 與順序相同,對應 `test_rules_have_same_sections[zh-CN]`;「以簡體中文顯示」沒有直接的測試,不寫進情境。

## Risks / Trade-offs

- [Purpose 不經 delta,歸檔時不會同步] → 在任務中直接改主 spec 的 Purpose,並在歸檔前確認。

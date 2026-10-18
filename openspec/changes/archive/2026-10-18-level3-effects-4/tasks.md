## 1. 測試先行

- [x] 1.1 `tests/test_level3.py` 第 4 批:23 張依效果文的行為測試(擲幣正 / 反、可選效果使用 / 不使用、選擇者、使用條件錯誤碼、時效);確認修改前失敗
- [x] 1.2 機制(含 D11 常駐效果在「効果を使えない」時失效、P-032 不能被 E-036 移除):魔力設為某值(M-035 跟著變動、與 P-011 後發者勝出兩個方向、對象離場、互相複製);M-047 兩種放出時機的離場回合、無視「不會被棄掉」;ジャマー無效事件卡與 M-026 連鎖;M-034 與 M-012 並列;P-020 的雙向保護與開始 / 結束階段不受影響;1 行動棄卡的時機限制
- [x] 1.3 改寫既有 P-011 測試與明細測試為「魔力設為某值」

## 2. 引擎機制

- [x] 2.1 `power_set` 取代 `power_zero`,明細項 `power_set`(design D1)
- [x] 2.2 `family` 判定與 `treated_as`,替換 `related_mamodo` 的魔物身分判斷(D2)
- [x] 2.3 依家族疊放、`_detach_top`、`scheduled_detach` 定時離場(D3)
- [x] 2.4 1 行動效果指令 `use_action_effect`(D4)
- [x] 2.5 ジャマー的觸發動作與事件卡快照、棄掉自己的費用(D5)
- [x] 2.6 擲幣確認鏈的 `set_heads`(D6)
- [x] 2.7 P-020 的 MP 保護與 `gain_mp(by=)`(D7)
- [x] 2.8 魔物效果防禦、S-087 固定合計魔力(D8)
- [x] 2.9 戰鬥外的魔書傷害(S-094)、M-048 合計魔力門檻、M-049 搭檔保護、P-025 非戰鬥任意頁、P-031 常駐禁止(D9)

## 3. 卡片登記

- [x] 3.1 23 張登記(依卡號排序,香草戰術 S-059 / S-091 註記)
- [x] 3.2 `data/pending_cards.json` 移除 23 張;第 1 組測試全過

## 4. 前端與 NPC

- [x] 4.1 行動欄:1 行動棄卡、魔物效果防禦按鈕;擲幣確認的「改成正面」;M-032 詢問;記錄、作用中效果與魔力明細文字(zh-TW / en / ja,`build_zh_cn.py`);瀏覽器測試
- [x] 4.2 NPC 能處理新指令與新決策(單元測試)

## 5. 驗證

- [x] 5.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 5.2 本機實際操作(附測試牌組;測試牌組已提供,使用者 2026-10-18 指示歸檔)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine`、`battle-ui` 主 spec(歸檔時)
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入第 4 批的解讀(Confirmed,2026-10-18;含 M-047 離場時機、M-035 / P-011 後發者勝出、P-032 範圍);`game-engine/design.md`:魔力明細的 `power_set`、1 行動效果、ジャマー的觸發動作、魔物效果防禦
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive level3-effects-4 -y`,在 `level3-effects-4` 分支提交;合併 main 與推送等使用者指示
- 第 5 批(S-088〜S-090、E-029 / E-037 / E-039 / E-041 / E-042)另開 change,先 explore(S-088〜S-090 需確認是否屬 S-026 類)

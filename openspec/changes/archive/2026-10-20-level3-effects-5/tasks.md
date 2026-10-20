## 1. 測試先行

- [x] 1.1 `tests/test_level3.py` 第 5 批:8 張依效果文的行為測試(擲幣正 / 反、選擇者、使用條件錯誤碼、時效);確認修改前失敗
- [x] 1.2 機制:結束階段 2 個以上效果時由回合玩家定序(含 M-047 離場)、只有 1 個時不詢問;事件卡上限;不能攻擊不能被 E-036 移除;傷害紀錄(保護者、免疫不算)

## 2. 引擎機制

- [x] 2.1 S-088 本来のコスト 0 的待命、S-089 宣告時選對象與明細項(design D1)
- [x] 2.2 S-090 回合結束時棄掉搭檔(D2)
- [x] 2.3 事件卡使用計數與上限(D3)
- [x] 2.4 E-037 互換、E-039 不能攻擊與翻頁限制(D4、D5)
- [x] 2.5 傷害紀錄與 E-041、E-042 的待命(D6、D7)
- [x] 2.6 結束階段效果的定序決策 `end_phase_order`(D8)

## 3. 卡片登記

- [x] 3.1 8 張登記(依卡號排序)
- [x] 3.2 `data/pending_cards.json` 清空;開放清單測試更新

## 4. 前端與 NPC

- [x] 4.1 結束階段定序的按鈕、`pick_mamodo_to_keep` 標題、記錄與作用中效果文字(zh-TW / en / ja,`build_zh_cn.py`);瀏覽器測試
- [x] 4.2 NPC 能處理新決策(單元測試)

## 5. 驗證

- [x] 5.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 5.2 本機實際操作(附測試牌組;測試牌組已提供,使用者 2026-10-20 指示歸檔)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine`、`battle-ui` 主 spec(歸檔時)
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入第 5 批的解讀(Confirmed,2026-10-20;含 S-088〜S-090 屬 S-026 類);`game-engine/design.md`:結束階段定序、事件卡上限、不能攻擊
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive level3-effects-5 -y`,在 `level3-effects-5` 分支提交;合併 main 與推送等使用者指示

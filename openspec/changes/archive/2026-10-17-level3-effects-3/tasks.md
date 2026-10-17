## 1. 測試先行

- [x] 1.1 `tests/test_level3.py` 第 3 批:27 張依效果文的行為測試(擲幣正 / 反、追加費用的選項與付費、使用條件錯誤碼、宣告時確定、戰鬥結束時生效、時效);確認修改前失敗
- [x] 1.2 機制:追加費用與 M-008 減費依序;MP 紀錄(含 P-021 擋下不計、E-004 歸零計入);S-068 排定期間可被 P-034 / E-036 移除;S-062 不重複;S-098 重用的次數與條件

## 2. 引擎機制

- [x] 2.1 宣告時的追加費用(design D1)
- [x] 2.2 戰鬥結束時生效的 `after_battle` 待命與 `attr_power`(D2)
- [x] 2.3 MP 紀錄欄位(D3)
- [x] 2.4 反擊傷害、攻擊時才生效的修正、魔物限定的 `no_attack_spell`、`spell_reuse`、M-037 頁範圍、`ScheduleNextSpellBonus` 時效、`redirect_damage`(D4)

## 3. 卡片登記

- [x] 3.1 エシュロス、ティオ、バリー、フリガロ 24 張與 E-028 / E-034 / E-035 登記(依卡號排序,香草戰術註記)
- [x] 3.2 `data/pending_cards.json` 移除 27 張;第 1 組測試全過

## 4. 前端與 NPC

- [x] 4.1 選項標籤 `extra_cost` / `reuse_spell`、作用中效果與記錄的文字(zh-TW / en / ja,`build_zh_cn.py`);瀏覽器測試
- [x] 4.2 NPC 能處理追加費用與新決策(單元測試)

## 5. 驗證

- [x] 5.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 5.2 本機實際操作(附測試牌組)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`battle-ui` 主 spec(歸檔時)
- [x] 6.2 `card-effects/design.md`:追加費用、戰鬥結束時生效、MP 紀錄的機制;「行為決定與理由」加入第 3 批的解讀(Confirmed,2026-10-17;含 S-098 重用方式、S-068 宣告時擲幣、S-103 目前無時機)
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive level3-effects-3 -y`,在 `level3-effects-3` 分支提交;合併 main 與推送等使用者指示
- 第 4 批(ガッシュ、ウマゴン、ダニー、キャンチョメ)另開 change,先 explore

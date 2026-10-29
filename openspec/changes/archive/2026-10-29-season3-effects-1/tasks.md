## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_1.py`:50 張中每張非香草卡至少一個依效果文寫的行為測試(擲幣正 / 反、可選效果、選擇者、使用條件的錯誤碼、時效);香草戰術與白板魔物各取代表卡驗證攻防與使用。執行並確認修改前失敗(卡片尚未開放或效果未註冊)
- [x] 1.2 機制測試:E-048 依魔物數重算與之後放出的魔物(FAQ Q1 / Q2)、M-064 跨回合仍有效、M-068 第 3 次被拒絕(`attack.used`)、Ex-036 對 M-069 也加且明細有來源、PR-004 名稱完全比對、Ex-007 下一場戰鬥沒用對應家族時消失、S-112 被保護時才翻頁;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 白板魔物:放出、攻防、作為戰術使用者、拒絕啟動效果(design D1);1.1 的白板魔物測試通過
- [x] 2.2 `DUR_GAME` 時效(D2);M-064 測試通過
- [x] 2.3 `power_per_own_mamodo` modifier(D3);E-048 測試通過
- [x] 2.4 `STATIC_TOTAL_POWER` 與明細項目 `static_total`(D4);Ex-036 測試與既有魔力勝負明細測試通過
- [x] 2.5 名稱比對的戰術加成與減費 `STATIC_SPELL_POWER`、`spell_named`(D5);PR-004 / PR-010 測試通過
- [x] 2.6 `spell_bonus` 待命的 `base_zero` / `base_delta`(D6);Ex-007 / Ex-035 測試與既有 P-007 / M-008 / P-023 測試通過
- [x] 2.7 魔物效果攻擊的 `per_turn` 與計數(D7);M-068 測試與既有 M-027 / M-039 測試通過
- [x] 2.8 `END_PHASE` 場上觸發加入結束階段效果清單(D8);PR-011 測試與既有結束階段定序測試通過
- [x] 2.9 `Coin.count` 可為函式(D9);E-046 測試通過
- [x] 2.10 `SpellRider.on_protected`(D11)與 S-109 的 `on_win` 擲幣(D10);S-109 / S-112 測試通過

## 3. 卡片登記

- [x] 3.1 50 張登記於 `effects/cards/` 對應檔案(依卡號排序;香草戰術補進 `spells.py` 開頭的清單)
- [x] 3.2 常駐效果同一卡號多張在場時各自生效(design D12):先寫測試(以測試替身放寬同名上限,兩張常駐魔力加成各自計入)並確認修改前失敗,再修改 `power_breakdown`;既有常駐效果測試照常通過
- [x] 3.3 `data/pending_cards.json` 移除 50 張;`tests/test_season3_cards.py` 的開放張數更新;`python -m pytest tests -m "not slow and not browser" -q` 全過

## 4. 前端與 NPC

- [x] 4.1 新事件與作用中效果的文字、明細項目 `static_total` 的標籤(zh-TW / en / ja,`build_zh_cn.py` 產生 zh-CN);新的決策種類若有,補 `choice.title.<kind>`;相關瀏覽器測試通過
- [x] 4.2 白板魔物的放大檢視不顯示效果區塊、場上沒有效果按鈕(瀏覽器測試)
- [x] 4.3 NPC 自我對戰牌組含這批卡(含白板魔物與 M-068)不卡住(既有 slow 自我對戰測試或新增一個)
- [x] 4.4 構築器的卡號順序(design D16):`compareCardNumbers` 用於卡池排序、代表卡與家族排列;新家族加進 `pool-filters.json`;`tests/test_pool_filters_ui.py` 通過

## 5. 驗證

- [x] 5.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine`、`deck-builder` 主 spec
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入這批的解讀(E-048 / Ex-007 類為 Confirmed(FAQ),Ex-027 與常駐效果疊加為 Confirmed,其餘依 design 表格的狀態)與新機制說明;相關規格指向新需求名稱(不含批號);`game-engine/design.md`:魔物效果攻擊次數、合計魔力的場上加成、結束階段的場上觸發
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive season3-effects-1 --skip-specs -y`(主 spec 已手動同步),在 `season3-effects-1` 分支提交;合併 main 與推送等使用者指示

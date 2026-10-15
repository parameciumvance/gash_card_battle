## 1. 測試先行

- [x] 1.1 `tests/test_level3.py`:依效果文寫 21 張卡的行為測試(擲幣正 / 反、使用條件不成立的錯誤碼精確比對、M-043 發動後傷害再變化仍無效、P-027 選項與ゾボロン除外、E-033 選卡與空頁、E-038 結束階段),以及「第 1 批不在尚未開放清單」;執行並確認全部因未實作而失敗
- [x] 1.2 保護相關:以對手魔物保護的選項 `player`、`protected` 事件的 `player` / `target_player` 測試;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 魔物卡的「將此卡棄掉」費用(design D1)
- [x] 2.2 `own_damage_bonus`:攻擊與【反擊】傷害加值;戰術自身傷害加值寫入 `attack_damage_delta`(D2)
- [x] 2.3 MP 保護 `mp_guard` 與 `mp_reduction_prevented` 事件(D3)
- [x] 2.4 本回合戰術相容 `spell_compat_attr`(D4)
- [x] 2.5 以對手魔物保護:可保護者含持有者、保護決策合併為一個函式、選項與 `protected` 事件改以持有者標示(D5)
- [x] 2.6 E-038 的結束階段 MP 待命、E-033 的棄牌區魔物卡選項規格(D7)

## 3. 卡片登記

- [x] 3.1 ブラゴ、ザバス、バーゴ、ゾボロン 16 張登記(依卡號排序,香草戰術註記於 spells.py)
- [x] 3.2 E-030 / E-032 / E-033 / E-038 / E-040 登記
- [x] 3.3 `data/pending_cards.json` 移除 21 張;1.1、1.2 的測試全過

## 4. 前端與 NPC

- [x] 4.1 行動記錄:`mp_reduction_prevented`、以對手魔物保護的 `protected`(zh-TW / en / ja,`build_zh_cn.py`)
- [x] 4.2 作用中效果的文字(`own_damage_bonus`、`mp_guard`、`spell_compat_attr`、`protect_with_opponent`、E-038 待命)
- [x] 4.3 保護決策時對手場上的魔物發光可選;保護演出移到受方魔書前再回到對手原位;瀏覽器測試
- [x] 4.4 NPC 保護判斷依選項的持有者找魔物,優先以對手魔物保護;測試
- [x] 4.5 決策種類:沿用既有 `choice.title.*`,新的選項標籤在 `app.js` 對應(若有)

## 5. 驗證

- [x] 5.1 `pytest` 全過;`openspec validate --all --strict` 與既有基準相比沒有新增失敗
- [x] 5.2 本機實際操作:M-033、P-027 保護、P-021 記錄(自由調查時間)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine`、`battle-ui`、`npc-opponent` 主 spec
- [x] 6.2 `card-effects/design.md`:第三彈分批方式、新機制(棄掉費用、`own_damage_bonus` 與 `damage_delta` 的差別、MP 保護、以對手魔物保護)、「行為決定與理由」加入第 1 批的解讀(Confirmed,2026-10-14 使用者確認);`game-engine/design.md` 保護者可為對手魔物;`battle-ui/design.md` 對手魔物的保護選擇與演出;`npc-opponent/design.md` 保護判斷
- [x] 6.3 capability map:`card-effects` 說明改為含第三彈(分批中)

## Workflow follow-up

- 歸檔:`openspec archive level3-effects-1 -y`,在 `level3-effects-1` 分支提交;合併 main 與推送等使用者指示
- 第 2 批(パピプリオ、ゼオン、ロップス、ウォンレイ + E-031 / E-036 / E-043)另開 change,先 explore

# Tasks

## 1. 先寫依效果文與新規則的測試

- [x] 1.1 新增測試(`tests/test_coin_subphase.py`):E-005 擲 2 枚,對手以 M-019 選第 2 枚,只有第 2 枚重擲(以固定的 RNG 驗證第 1 枚不變、只多消耗 1 次 RNG)
- [x] 1.2 新增測試:擲幣者有 M-012、對手有 M-019 時,先出現 `coin_confirm`(擲幣者),擲幣者保留後才出現 `opp_coin_redo`(對手)
- [x] 1.3 新增測試:擲幣者用 M-012 後輪到對手;對手不使用後再輪到擲幣者(可用 M-034);雙方連續不使用時依當下結果解決
- [x] 1.4 新增測試:`opp_coin_redo` 的選項為不使用加每枚一個;非法回應以 `choose.invalid` 拒絕並保留 pending;雙方都沒有可用效果時不出現詢問
- [x] 1.5 新增測試:子階段中使用 M-012、M-034、M-019 時,對手場上有可用的 M-026 也不出現ジャマー的詢問,效果照常生效;非戰鬥中擲幣事件卡經過子階段後,行動權與沒有使用這些效果時相同(這兩項是確認既有行為,預期修正前後都通過;若修正前就失敗,列出並另行處理)
- [x] 1.6 確認 1.1~1.4 在修正前失敗(錯誤碼與斷言精確,不是停在其他 pending)

## 2. 引擎:擲硬幣子階段

- [x] 2.1 `primitives.py`:確認鏈改為輪替(`data` 的 `turn` / `passes`),M-019 改為重擲選定的 1 枚、`opp_coin_redo` 的回應檢查合法性;更新 `flip_coins` 與模組說明;1.x 測試通過
- [x] 2.2 依新規則改寫既有測試中依舊順序或整組重擲的斷言(`tests/test_effect_characterization.py`、`tests/test_cards.py`、`tests/test_battle_info.py` 及其他以 `opp_coin_redo` / `True` 回應的測試),每處改寫在 commit 前列出;`python -m pytest tests -q -m "not slow"` 除既有的卡圖相關失敗外全部通過

## 3. 前端與規則頁

- [x] 3.1 `frontend/app.js` 的 `choiceLabel` 新增 `opp_reflip`(標明第幾枚與目前結果);`frontend/i18n/{zh-TW,en,ja}.json` 新增 `choice.opp_reflip`,執行 `python tools/build_zh_cn.py` 產生簡中;`tests/test_i18n_languages.py` 通過
- [x] 3.2 新增或擴充瀏覽器測試:對手擲 2 枚時,自己的 M-019 選項標明第 1、2 枚與目前結果,不含支付 MP(`tests/test_battle_info_ui.py` 或同類檔案)
- [x] 3.3 規則頁「擲硬幣」段落(`frontend/i18n/rules.{zh-TW,en,ja}.json`)補上子階段:擲幣者先使用影響硬幣的效果,之後輪替,雙方都不使用時依結果解決;重跑 `build_zh_cn.py`;`tests/test_rules_page.py`、`tests/test_i18n_languages.py` 通過

## 4. NPC 與整體

- [x] 4.1 `python -m pytest tests/test_npc.py tests/test_npc_room.py -q` 通過(含自我對戰)

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回 `game-engine`、`card-effects`、`effect-tree`、`battle-ui` 主 spec;`openspec validate --all --strict` 通過且沒有新增說明過長的提示
- [x] 5.2 更新 design:`card-effects/design.md`「擲幣重擲(M-012 / M-019)」改寫確認鏈為子階段;「行為決定與理由」新增「擲硬幣子階段的順序」(`Project Decision`)與「M-019 由使用者選重擲哪一枚」(`Confirmed`);`game-engine/design.md` 視需要補上子階段;確認 capability map 不需更新
- [x] 5.3 `todo.md` 移除「鈴芽探病禮重擲」
- [x] 5.4 依使用者指示歸檔並提交

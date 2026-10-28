# Tasks

## 1. 數值徽章

- [x] 1.1 先寫瀏覽器測試(`tests/test_effect_visibility_ui.py` 或新檔):卡池與放大檢視中 M-001 的魔力只在徽章、S-001 的費用只在徽章,資訊列沒有「魔力」「費用」;放大檢視的魔力徽章為兩行「魔力」/「4000」,盤面的魔力徽章只寫「4000」;缺卡圖時徽章仍在。確認修正前失敗
- [x] 1.2 `cardEl` 一律產生魔力 / 費用徽章,資訊列移除費用與魔物的魔力;放大檢視顯示徽章並由徽章著色;魔力徽章依容器切換兩行或只寫數值(`frontend/app.js`、`frontend/style.css`);1.1 通過
- [x] 1.3 依新呈現改寫既有測試:`tests/test_effect_visibility_ui.py`(放大檢視著色改看徽章)、`tests/test_level3_ui.py`(「費用 3」改看費用徽章)及其他依賴資訊列費用 / 魔力或「魔力 N」徽章文字的測試,改寫處在提交前列出;`python -m pytest tests/test_effect_visibility_ui.py tests/test_level3_ui.py tests/test_builder_card_info_ui.py -q` 通過
- [x] 1.4 以截圖確認桌面與手機寬度:盤面魔物的徽章不蓋住卡名、放大檢視的兩行徽章與費用徽章位置正確(有卡圖與缺卡圖各一)

## 2. 對決舞台的攻防卡面

- [x] 2.1 先寫瀏覽器測試:宣告攻擊後(戰鬥開始確認)舞台攻擊方顯示魔物與戰術卡面;防禦宣告前為「等待防禦宣告」、宣告後為防禦卡面;不防禦時為「不防禦」;無戰術攻擊顯示固定魔力來源卡;攻擊被無效時有「無效」標記;點擊卡面開純展示放大檢視。確認修正前失敗
- [x] 2.2 `renderBattleStage` 加上攻防卡面,固定魔力來源卡的判斷與 `anim.js` 的對峙演出共用;舞台卡面尺寸以 CSS 變數分桌面 / 手機組;2.1 通過,既有舞台相關測試(`tests/test_timing_ui.py`、`tests/test_battle_info_ui.py` 等)通過
- [x] 2.3 以截圖確認桌面與手機寬度的舞台:卡面不擠壓合計與時機指示,手機行動列仍固定在底部

## 3. 整體

- [x] 3.1 `python -m pytest tests -q -m "not slow"` 除既有的卡圖相關失敗外全部通過;瀏覽器測試(`-m browser`)中與卡面、舞台相關的檔案通過

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui` 主 spec,新需求放在「盤面的狀態與對決舞台」之後;`openspec validate --all --strict` 通過且沒有新增說明過長的提示
- [x] 4.2 更新 `battle-ui/design.md`:卡片元件的數值徽章(唯一呈現、兩種寫法)與對決舞台的卡面;確認 `deck-builder` 規格不需修改(構築器卡面的費用 / 魔力改由徽章呈現,沿用 battle-ui「文字卡面與卡圖」);確認 capability map 不需更新
- [x] 4.3 `todo.md` 移除「魔力標籤分行」「戰鬥時就顯示咒語圖」
- [x] 4.4 依使用者指示歸檔並提交

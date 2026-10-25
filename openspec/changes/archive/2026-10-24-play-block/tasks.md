# Tasks

## 1. 引擎與快照

- [x] 1.1 先寫測試並確認修改前失敗:`tests/test_play_block.py` 斷言翻開頁的 `play_block`(M-046 `spell_only`、場上 3 隻 `field_full`、M-007 無ゴフレ `no_base` / 有則 null、同名 `same_name`)、搭檔頁的 `targets` 與 `play_block`(M-047 在場時ガッシュ・ベル的搭檔可放出)、對手視角不含這些欄位
- [x] 1.2 `engine.py` 抽出 `play_block` 與 `partner_targets`(design「查詢函式回傳錯誤碼」),`_play_card` 改經由它們判斷;既有 `play.*` 錯誤碼的測試不變,`python -m pytest tests -m "not slow and not browser" -q` 通過
- [x] 1.3 `views.py` 的 `_player_view` 對持有者視角的魔物 / 搭檔頁加欄位,1.1 的測試通過

## 2. 前端

- [x] 2.1 先寫瀏覽器測試並確認修改前失敗:M-046 的「放出」停用並顯示原因、場上 3 隻時停用、M-047 在場時ガッシュ・ベル搭檔可放出並裝上
- [x] 2.2 `app.js` 的 `pageButtons` 依 `play_block` 停用並顯示 `error.play.*`;`partnerTargets` / `pickPartnerTarget` 改用 `targets`;刪除不再使用的 `ui.play.no_mamodo` / `ui.play.partner_exists`(zh-TW / en / ja,`tools/build_zh_cn.py` 重建 zh-CN);2.1 與既有搭檔選擇的瀏覽器測試(兩隻 M-024)通過

## 3. 驗證與收尾

- [x] 3.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 沒有新增失敗
- [x] 3.2 Reconciliation:`battle-api/design.md` 記放出可否由引擎單一判斷、快照附 `play_block` / `targets` 的理由;`battle-ui/design.md` 記前端不再自行比對搭檔對應

## Workflow follow-up

- 使用者指示後歸檔並提交(歸檔時同步 delta spec)。

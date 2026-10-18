## 1. 測試先行

- [x] 1.1 引擎 / API:本機模式回合 1 由玩家 1 先攻、沒有先攻擲幣、有 `first_player_set`;NPC 與線上照常擲幣;保護決策的 `pending.info.damage` 對雙方與觀戰者相同(魔書含 `lethal`、魔物含 `injured`);確認修改前失敗
- [x] 1.2 瀏覽器:金手指的目前頁摘要與網格標記;保護提示的傷害文字(魔書、耗盡加註、已負傷魔物);確認修改前失敗

## 2. 實作

- [x] 2.1 `new_game` 的 `first_player`、`_start_game` 本機模式傳入;`first_player_set` 的記錄文字(design D2)
- [x] 2.2 `_protect_choice` 設定 `pending.info.damage`(D3)
- [x] 2.3 金手指面板的摘要與網格標記(D1)
- [x] 2.4 保護提示的傷害說明;i18n(zh-TW / en / ja,`build_zh_cn.py`)(D4)

## 3. 驗證

- [x] 3.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 3.2 本機實際操作

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 回 `game-engine`、`battle-api`、`battle-ui` 主 spec(歸檔時)
- [x] 4.2 `battle-ui/design.md`(金手指提示、保護提示)、`battle-api/design.md`(pending.info 的保護內容)、`game-engine/design.md`(先攻)

## Workflow follow-up

- 歸檔:`openspec archive investigation-ux -y`,在 `investigation-ux` 分支提交;合併 main 與推送等使用者指示

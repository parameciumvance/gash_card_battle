# Tasks

## 1. 引擎:獨立卡區與 MJ12 規則

- [x] 1.1 先寫測試並確認失敗:雙方戰鬥階段可放出 MJ12、同名拒絕、戰鬥中不能放出 / 使用、每回合 1 次、棄掉進棄牌區、不受魔物 / 搭檔效果限制(design D1、D2)。
- [x] 1.2 實作 `FieldCard`、`field_cards`、`play_block` / `_play_card`、`use_field_ability` 的 `zone: "field"`、`discard_field_card`。

## 2. 卡片效果

- [x] 2.1 先寫測試並確認失敗(依效果文,含使用 / 不能使用、選擇者、非法選擇):MJ-001(保護)、MJ-002 / 005(戰術與魔物效果的攻防、回合結束失效)、MJ-003(魔物 / 搭檔、沒有可選時拒絕)、MJ-004(揭露只給使用者、MP)、MJ-006(反減、雙方各 1 次、E-004 歸零、P-021)、Ex-074(條件、選擇、非法選擇保留 pending)。
- [x] 2.2 實作(design D3):`side_power`、MJ-003 的合併選擇、MJ-006 掛鉤、Ex-074;新決策種類補 `choice.title.*`。

## 3. 快照、NPC、資料

- [x] 3.1 快照 `field_cards` 與翻開頁 MJ12 的 `play_block`(design D4),測試。
- [x] 3.2 NPC 候選指令含放出 MJ12 與使用其效果;自我對戰含 MJ12 的魔書不出錯(slow)。
- [x] 3.3 `pending_cards.json` 移除 MJ-001~006、Ex-074。

## 4. 前端

- [x] 4.1 先寫瀏覽器測試並確認失敗:放出按鈕、效果按鈕與停用原因、`field` 決策目標、動畫端點、行動記錄文字。
- [x] 4.2 實作(design D5)。

## 5. 驗證與文件

- [x] 5.1 快速測試組與相關瀏覽器測試、新的 slow 測試;`openspec validate mj12-cards --strict`。(快速組 1697 項;非 slow 瀏覽器測試 521 項;MJ12 自我對戰 9 局。金手指與構築器的產品 / 卡池測試改為 LEVEL:4、拡張シート3 已有開放的卡)
- [x] 5.2 reconciliation:`card-effects/design.md`(行為決定與理由)、`game-engine` / `battle-ui` design、capability map。
- [x] 5.4 使用者回報:檢視對手頁面的對話框中,效果文長短不同的卡高度不一致(MJ-004 會用到)。先寫等高測試並確認失敗,再讓卡片撐滿外框。
- [x] 5.3 使用者確認。(2026-11-08 使用者同意歸檔)

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec;歸檔後以 `--no-ff` 合併回 `dev`。

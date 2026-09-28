## Why

`docs/specification-guide.md` 定義了本專案的規格制度:`spec.md` 寫現行行為、capability 的 `design.md` 寫現行設計與仍有效的理由、`capability-map.md` 負責導航,行為解讀要標註確認狀態。目前的文件還不符合:設計與解讀集中在單一的 `openspec/design.md`,沒有 capability map,解讀的確認狀態用的是非正式說法,部分解讀的行為結果沒寫進 spec,幾個 spec 的 Purpose 過時或是 TBD。另外,專案負責人決定依效果文拿掉 P-018「魔本在第一頁時不能使用」的限制。

## What Changes

- 新增 `openspec/capability-map.md`:系統概觀、11 個 capability 的責任、關係與主要 flow、建議閱讀入口、spec / design 覆蓋程度。
- 把 `openspec/design.md` 拆到各 capability 的 `design.md`(`game-engine`、`effect-tree`、`card-effects`),刪除 `openspec/design.md`。
- `card-effects/design.md` 的「行為決定與理由」依指南 §7.4 格式改寫,並標註專案負責人核可的確認狀態。
- **行為變更**:P-018 在魔本第一頁也能使用(棄掉卡片、不回翻、仍受「合計1回」限制)。
- `card-effects` spec 補上既有但未寫入的行為:S-026 / S-057 擲出正面時不詢問是否使用;回翻 0 張不算用過回翻效果。
- `game-engine` spec 補上「只有回合玩家能宣告攻擊」的情境,供 `card-effects` 引用。
- 更新過時或 TBD 的 Purpose:`effect-tree`、`docker-deployment`、`standalone-release`。
- `AGENTS.md` 的規格流程改為指向指南;`openspec/config.yaml` 的 context 與 tasks 規則改為依指南;README 的文件指引改為指向 capability map。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:P-018 第一頁可用(行為變更);補上 S-026 / S-057 不詢問、回翻 0 張不算用過兩項既有行為的情境。
- `game-engine`:「戰鬥開始確認」補上非回合玩家不能宣告攻擊的情境(既有行為)。

## Impact

- 程式:`src/gash/engine/effects/tree.py`(P-018 的使用條件)。
- 測試:`tests/test_level2.py`(P-018)。
- 文件:`openspec/capability-map.md`(新)、`openspec/specs/{game-engine,effect-tree,card-effects}/design.md`(新)、`openspec/design.md`(刪)、三個 spec 的 Purpose、`AGENTS.md`、`openspec/config.yaml`、`README.md`。
- API、前端不受影響。

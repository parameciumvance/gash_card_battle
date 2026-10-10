## Context

- 首頁入口寫在 `index.html` 的 `#landing-cards`,順序就是 DOM 順序;標題與簡介由 `renderLanding()` 依 i18n 鍵 `ui.landing.<key>` / `ui.landing.<key>_desc` 填入,設定頁標題也用 `ui.landing.<mode>`。
- 本機測試模式在規格與程式中有大量技術性提及(「本機房」、`mode=local`、`isLocal()`、`local-test-mode` capability、測試的 docstring)。
- 動機見 proposal.md「Why」。

## Goals / Non-Goals

**Goals:** 玩家看到的名稱不再像一種對戰模式,入口位置不再緊接在兩種對戰之後。

**Non-Goals:** 不改功能、建房模式、入口 id(`entry-local`)、capability 名稱。

## Decisions

### D1:只改顯示名稱,技術名稱保留

- 改動的 i18n 字串:
  - `ui.landing.local`:入口與設定頁標題。
  - `ui.landing.local_desc`:入口簡介(見 D2 後段)。
  - `error.room.not_local`:金手指端點在其他模式下的錯誤。
  - `error.room.not_joinable`:嘗試加入本機房時的錯誤。
- 規格與程式中的「本機房」「本機測試模式」「`mode=local`」是技術名稱,保留不改。只在 `battle-ui`「首頁入口」寫明「自由調查時間是本機測試模式對玩家顯示的名稱」,作為兩者的對照。
- 替代方案:全面改名(含 capability `local-test-mode`、規格用語、測試 docstring)。改動面大,但對玩家沒有差別;技術名稱描述的是「單一畫面操作雙方」這個實作,反而比顯示名稱更準確。

### D2:各語言名稱(Agent 起草,待使用者審閱)

| 語言 | 名稱 | `error.room.not_local` | `error.room.not_joinable` |
|---|---|---|---|
| zh-TW | 自由調查時間 | 僅自由調查時間與 NPC 對戰開放 | 自由調查時間的房間不可加入 |
| zh-CN | 由工具產生 | 由工具產生 | 由工具產生 |
| en | Free Investigation | Only available in Free Investigation and NPC games | Free Investigation rooms cannot be joined |
| ja | 自由調査タイム | 自由調査タイムと NPC 対戦だけで使える | 自由調査タイムのルームには参加できない |

簡介 `ui.landing.local_desc`(使用者要求強調沒有電腦對手):

| 語言 | 簡介 |
|---|---|
| zh-TW | 沒有電腦對手,在同一畫面操作雙方;附金手指面板 |
| en | No computer opponent: you control both sides on this screen; includes the cheat panel |
| ja | コンピューターの相手はいない。1つの画面で両方を操作する。チートパネルつき |

「操作雙方」涵蓋一人操作與兩人輪流,不再只寫「兩人共用」:誤認的玩家就是一個人在用。

### D3:入口順序

NPC 對戰、與朋友對戰、牌組構築、自由調查時間、規則、意見回報。只調整 `index.html` 的 DOM 順序;各入口的點擊行為都綁在 id 上,不受順序影響。桌面三欄排版下,第一列是 NPC 對戰、與朋友對戰、牌組構築,自由調查時間移到第二列最前面。

## Risks / Trade-offs

- [老玩家找不到原本的入口] → 名稱與位置都改了,簡介仍提到金手指,可辨識。下一版的更新內容應說明這次改名。
- [規格中技術名稱與顯示名稱不同] → 在「首頁入口」需求與 `battle-ui/design.md` 寫明對照。

## Migration Plan

純前端文字與順序,部署即生效。

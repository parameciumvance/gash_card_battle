## Context

範圍與動機見 proposal.md。以下只記錄需要擴充引擎的地方，以及效果文沒有寫清楚、需要解讀的部分。

既有機制的對應:

| 卡 | 沿用 |
|---|---|
| E-044 | E-012 的 `DeployableMamodoInOwnBook` / `PlayMamodoFromBook` 與 E-027 的 `AttachablePartnerPagesInOwnBook` / `SlotsForBookPartner` / `AttachPartnerFromBookPage`,限目前翻開的頁 |
| Ex-003 | M-045 的 `PeekOpponentOpenPages` + `OpponentOpenPageCards` + `DiscardFromOpponentBook`(不限卡片類型),`per_game=True` |
| Ex-022 | `TurnPagesForward(target="opponent")` + E-039 的 `TurnOwnPageLimitedThenGainMp(amount=0)` |
| Ex-032 | M-020 / M-021 / M-041 的 `OwnBookPartnerNamed` + `AttachPartnerFromBookPage(slot=self_slot)` |
| Ex-045 | M-018 的「檢視後判斷」:`PeekOpponentOpenPages` + `When(...)` + `TurnPagesForward(target="opponent")` |
| M-060 | `activated(mode="discard", timing="nonbattle", own_turn=True)`(同 M-018 的「自分のバトルフェイズに」)+ `TurnPagesForward(target="opponent")` |
| M-063 | `activated(mode="declare", timing="nonbattle")`,條件為對手版的 `OwnBookAtLastPage`(M-030) |
| P-036 | E-027 的放出搭檔節點 |
| PR-007 的回翻 | P-018 的 `TurnOwnPagesBackOncePerTurn` |
| E-045 的檢視 | E-016 的 `RevealOpponentBook` + `OpponentBookCards` + `DiscardFromOpponentBook`,沒有對象時 `AwaitBookReviewEnd` |

## Goals / Non-Goals

**Goals:**
- 12 張全部依效果文實作並開放，每張非香草卡至少一個依效果文寫的行為測試。
- 「具有限制效果的卡」由效果的實作推導，新增卡片時有守門測試防漏。
- 「每回合 1 次以卡號計」寫進規格、design 與規則頁。

**Non-Goals:**
- 第 5 批的卡(Ex-025、Ex-026、Ex-034、Ex-037、M-065、P-037、P-039、P-041、PR-001、PR-006)與 M-058。
- 改變既有卡的行為。

## Decisions

### D1 限制種類的標示與推導(E-045)

- 新增對照表 `RESTRICTION_KINDS`(限制旗標 → 限制種類 `spells` / `protect` / `mamodo_effects`)。與 `RESTRICTION_CATEGORIES`(移除與無視用)分開：依 atwiki 卡頁 FAQ,`NO_ATTACK`(E-039「攻撃できない」)算 `spells`,但 E-039 寫明「取りのぞけない」,不能被 E-036 / P-034 移除。
- 不用限制旗標的效果節點加類別屬性 `restricts: tuple[str, ...]`(例如 E-013 的 `ScheduleNoProtectBookNextBattle`、S-035 / S-081 的「這次傷害不能保護」);登記表也標示種類(P-031 的 `block_opponent_family` 為 `mamodo_effects`)。
- 推導寫在 `tree.py`(`effects/` 只放 `__init__` / `registry` / `primitives` / `tree` 四個檔，有測試檢查)。推導函式 `restriction_kinds(number)`:走訪該卡所有掛鉤的效果樹(`EFFECTS`),收集節點的 `restricts` 與節點限制旗標換算的種類，再加上登記表標示的種類。具有任一種即「具有限制效果」。
- E-045 的對象:對手魔書中未離開、不在最後一頁(game-engine「最後一頁的戰術」)、`restriction_kinds` 非空的卡。
- 不採用手寫卡號清單：使用者 2026-10-31 認為不自然，新增卡片時也容易漏。
- 守門測試(`tests/test_restriction_kinds.py`):
  - 掃描所有卡的 `effect_ja`,含限制字樣的卡(「使えない」「できない」搭配「術」「かば」「魔物の効果」「攻撃」)必須 `restriction_kinds` 非空，或列在測試的排除名單並附理由。
  - 排除名單:E-031、E-036、M-038、M-042(解除或無視限制),M-058(卡片規則，使用者 2026-10-31),以及字面命中但不是這三種限制的卡(如「パートナーの効果を使えない」「イベントカードを使えない」「合計1回しか使えない」),逐張附理由。
  - 尚未開放的卡不檢查(未實作就無從推導),開放時自動納入。
  - 另以 FAQ 清單核對：已實作的 FAQ 列出的卡，加上 Ex-044、P-031,都必須具有限制效果。

### D2 依序放出 2 隻魔物(Ex-046)

- 使用條件：存在一對可同時放出的魔物卡(場上至少空 2 格、兩張彼此不同名且不與場上同名)。疊放的魔物(`STACK_ON`)不列入(使用者 2026-10-31)。
- 第 1 張的選項只列出放出後仍有第 2 張可選的卡;第 2 張在第 1 張放出後以當時的場面重新計算。
- 新增查詢 `DeployableMamodoInOwnBook(no_stack=True)`,以及「放出後仍有第 2 張」的過濾。

### D3 棄掉與放出魔物(M-062)

- 「片方または両方を、この順で」:先 `Choose(OrSkip(自己場上的魔物))`,再 `Choose(放出的魔物卡)`;第二步在第一步選了「不棄掉」或場上已沒有魔物時不提供「不使用」。
- 依 atwiki 卡頁 FAQ Q1 / Q2:棄掉後場上仍滿 3 隻時不能放出(第二步沒有選項就略過);只剩 1 隻時，棄掉它的選項只在魔書中有可放出的魔物時提供。
- 使用條件:(場上 ≥ 2 隻)或(有可放出的魔物卡)。只有 1 隻且沒有可放出的卡時，兩個效果都不能用。
- 棄掉自己場上的魔物沿用一般棄掉(搭檔一起棄掉);棄掉的是 M-062 自己時，效果照常解決到最後。

- 只有 1 個可選項時照引擎慣例自動選(`Choose` 的 `auto_single`)。

### D4 以使用費用後的場面判斷使用條件(P-036)

- 搭檔的「將此卡棄掉」使用條件原本在付費前判斷。P-036 要判斷「棄掉這張搭檔後能不能放出搭檔」:條件函式以假設這張搭檔已離場的場面判斷(這隻魔物視為沒有搭檔，場上沒有同名的高嶺清麿)。
- 新增查詢參數 `AttachablePartnerPagesInOwnBook(excluding_self=True)`,只在條件判斷時使用;效果解決時這張搭檔已棄掉，照一般判斷即可。
- E-010 借用時不棄掉搭檔，`self_slot` 不是使用者的魔物，照一般場面判斷;借用者魔書中沒有可放出的搭檔時以 `ability.condition` 拒絕(對象不存在的使用條件)。

### D5 棄掉自己這張事件卡(PR-007)

- 新節點 `DiscardThisEventFromBook`:把正在使用的事件卡從自己魔書移到棄牌區(`discard_from_book`),該頁變成空頁，發出 `card_discarded`(zone = book)。
- 「そうしたなら」:這張卡一定能棄掉，不需要分支;之後執行 `TurnOwnPagesBackOncePerTurn(leaves=2)`。

### D6 每回合 1 次以卡號計

- 依官方規則書第 20 頁:「将此卡棄掉→」的效果，同一回合棄掉後再放出相同編號的卡也不能再用。「宣告使用→」「MP を減らす→」只寫「1つの効果は、1ターンに1回」,以卡號計是推論，使用者 2026-10-31 確認三種一致。
- 程式不變(`used_abilities` 的鍵本來就是 `zone:卡號`);寫進 game-engine 規格與 design,規則頁「效果」一節補一句，四語。

### D7 解讀與確認狀態

| 卡 | 解讀 | 狀態 |
|---|---|---|
| E-044 | 依一般放出的規則(`play_block`);搭檔有多隻可裝的魔物時由使用者選;對手回合的事件卡(卡片資料「相手のターン」) | Inferred |
| E-045 | 不當使用條件(同 E-016);最後一頁除外(game-engine 規則) | Confirmed(使用者 2026-10-31) |
| E-045 | 「具有限制效果的卡」依 FAQ 清單 + Ex-044 + P-031,M-058 不算 | Confirmed(使用者 2026-10-31) |
| Ex-003 / M-063 | 沒有寫「自分のターン」,不限回合;戰鬥中不能使用 | Confirmed(使用者 2026-10-31) |
| Ex-003 | 最後一頁除外(game-engine 規則);沒有可棄的卡時只檢視 | Inferred |
| Ex-022 | 已受合計 1 次限制時只翻對手魔書 | Inferred |
| Ex-032 | 裝在這隻キッド(同 M-020) | Confirmed(使用者 2026-10-31) |
| Ex-045 | 已使用、仍在頁上的事件卡也算 | Confirmed(使用者 2026-10-31) |
| Ex-046 | 依序選、第 2 張重算;排除疊放 | Confirmed(使用者 2026-10-31) |
| M-062 | 依卡頁 FAQ Q1 / Q2 | Confirmed(使用者 2026-10-31) |
| P-036 | 以棄掉後的場面判斷使用條件 | Confirmed(使用者 2026-10-31) |
| PR-007 | 事件卡移到棄牌區、該頁變空頁 | Confirmed(使用者 2026-10-31) |

## Risks / Trade-offs

- [守門測試的字樣比對太寬或太窄] → 太寬時排除名單會變長，但每張都有理由;太窄時可能漏掉寫法特殊的卡。以 FAQ 清單核對補強，新增寫法時擴充字樣。
- [效果樹走訪漏掉不在 `EFFECTS` 的實作] → 守門測試會讓這類卡失敗，再補標示。
- [Ex-032 的對象「ナゾナゾ博士」(Ex-037)在第 5 批才開放] → 這批開放後暫時沒有對象;測試直接把 Ex-037 放進魔書。

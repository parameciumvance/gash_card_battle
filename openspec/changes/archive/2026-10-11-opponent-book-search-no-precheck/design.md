## Context

- M-011:`reg.activated(..., condition=HasOptions(OpponentBookCards("mamodo")))`;E-016 / E-017:`reg.event(..., when=HasOptions(OpponentBookCards(...)))`。`when` 同時決定快照的 `condition_ok`。
- 效果樹的 `Choose` 在沒有選項時直接結束(不進 pending、不執行 then),所以 `RevealOpponentBook` 之後若沒有對象,自然不棄卡;E-016 / E-017 的 MP 減少在 `DiscardFromOpponentBookPayCost` 內(then),也不會執行。

## Goals / Non-Goals

**Goals:** 三張卡不再預先檢查對手魔書的對象。

**Non-Goals:** 不改 S-048 / S-043 等以自己已知資訊為條件的卡;不改 `Choose` 的行為。

## Decisions

### D1:移除條件,不加新節點

只刪掉 `condition` / `when`。`Choose` 在沒有選項時直接結束,這正是「檢視後沒有可選的對象」的行為,不需要另外加節點。

### D2:與 S-048 規則的區別

「選不到對象就不能使用」只適用於使用者在使用前就知道的資訊(自己的魔書、場面)。看對手隱藏資訊才知道的對象,不能當使用條件,否則拒絕或停用本身就洩漏資訊。記在 `card-effects/design.md`「行為決定與理由」(Confirmed,專案負責人指示)。

### D3:前端顯示整本

- 實作後使用者發現:M-011 在對手沒有魔物時,什麼都沒看到。原因是 `book_revealed` 事件雖然帶整本內容(伺服器只送給檢視者),前端只寫成記錄;對手魔書只透過挑卡網格顯示,而網格只有可選的頁有卡面。
- 前端在即時批次收到帶 `cards` 的 `book_revealed` 時,記在 `REVEALED[被檢視者]`(只在該回合有效)。`showBookReview` 對沒有 `book` 的一方,以它補上非候選頁的卡面。
- 沒有可選的卡時(停在結束檢視),演出結束後自動開啟唯讀網格,標題註明。有挑卡決策時維持「由決策提示的按鈕開啟」的既有規則。(D4 之後結束時機由決策決定,見 D4。)

### D4:檢視阻塞對手行動

- 使用者要求:檢視中對手不能行動,以免看不到對手的行動過程。有對象時本來就停在挑卡決策;沒有對象時原本效果立即結束、行動權交出。
- 三張卡改為 `When(HasOptions(X), then=Choose(X, auto_single=False, ...), otherwise=AwaitBookReviewEnd())`:
  - `Choose.auto_single=False`:唯一對象也建立決策(使用者選擇:檢視一定等玩家操作才結束,規則單純)。其他卡的預設不變。
  - `AwaitBookReviewEnd`:新的停點節點,決策種類 `end_book_review`,只有一個選項「結束檢視」(value None),選項附整本未離開頁的卡面。pending 的選項只送給決策者,所以重新整理後仍能檢視,也不洩漏給對手與觀戰者。
  - `HasOptions` 增加 `test(game, ctx)`,可直接當 `When` 的條件。
- 逾時代打與 NPC 依既有規則選第一個選項,即結束檢視。
- 前端:結束檢視的選項顯示為按鈕,另給開啟對手魔書的按鈕;整本卡面優先取自這個決策,挑卡決策期間以 `book_revealed` 補上非候選頁;決策結束後不再提供,網格隨之關閉。

### D5:目標都在魔書 / 棄牌區時自動開啟

- 推翻 board-targeted-choices D4「決策開始時不自動開啟」。當時的理由是網格會蓋住場面;但網格可以關閉,關閉後同一決策不再自動跳出,「決策時可查閱場面」仍做得到,而常見的連續決策(M-025:棄牌區 → 魔書空頁)每步都要多按一次。使用者指定改為自動開啟。
- `autoOpenPick()` 在每批事件的演出結束後執行:以 pending 的 kind、決策者、來源、選項當鍵,同一鍵只自動開啟一次;`PICK` 有場上目標(`slot`),或目標分散在多本魔書 / 棄牌區時不開。
- 檢視對手魔書沒有可選的卡(`end_book_review`)也走這條路:它把對手魔書加進 `PICK.books`,所以自動開啟;原本專為 `book_revealed` 寫的自動開啟移除。

## Risks / Trade-offs

- [玩家在沒有對象時用掉一次性的 M-011] → 依效果文本來就是這樣;檢視本身仍有資訊價值。

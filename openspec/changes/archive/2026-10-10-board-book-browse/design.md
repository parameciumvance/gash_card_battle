## Context

動機見 proposal.md。相關現況(`frontend/app.js`):

- `renderBookBlock(p, ps)` 畫魔書區:書皮 `.book-cover`(固定寬高)內兩個頁位,固定為 `ps.pos`、`ps.pos + 1`。翻開的頁用 `openPageEl`(可操作、可被選取時發光),已離開的頁用 `cardBackEl(pg, true)`,超出範圍用 `.page-void`。
- 引擎的 `pos` 一律是偶數且 ≥ 2(翻頁、受傷、回翻都以 2 頁為單位,回翻最少到 2),所以目前對頁一定是 2–3、4–5……30–31 或 32(單頁)。魔書已翻完時 `pos` 可到 34。
- 持有者本人的快照有 `book`(32 頁卡號)與 `consumed_pages`;「查閱己方魔書」網格(`showBookReview`)已用這些資料畫出每頁狀態,排法是 [1]、[2,3]……[30,31]、[32]。
- 動畫管線 `Anim.apply` 先量測重繪前的 DOM(`.book-cover`、帶 `data-page` 的頁位)再演翻頁動畫,之後才重繪。

## Goals / Non-Goals

**Goals:**
- 在場上原位翻閱自己的魔書,隨時能回到目前頁。

**Non-Goals:**
- 不取代「查閱己方魔書」網格(一次看全部、可在決策中選頁)。
- 不提供翻閱對手的魔書。
- 翻到其他對頁時不能出牌或選取。

## Decisions

### D1:翻閱狀態只存在前端,以「對頁起點」記錄

- `BOOK_BROWSE = {}`,鍵為玩家,值為 `{start, pos}`:`start` 是正在檢視的對頁起點(0 代表只有第 1 頁的對頁,2、4……30,32 代表只有第 32 頁的對頁),`pos` 是開始翻閱時的目前頁。沒有項目就是在目前頁。
- 左右鍵:`start ∓ 2`,範圍 0–32;到頭 / 到尾時停用。從目前頁開始翻時以 `min(pos, 32)` 為起點。
- 回到目前頁:刪除該玩家的項目。
- **自動回到目前頁**:重繪時若 `S.players[p].pos !== BOOK_BROWSE[p].pos`(自己的魔書被翻動),刪除項目。其他更新不影響。
- 只有 `ps.book` 存在(快照含持有者完整魔書)時才顯示左右鍵,也就是自己的魔書;本機測試模式雙方都有。
- 替代方案:存在 localStorage。不採用:翻閱是暫時的檢視,重新整理後回到目前頁比較自然。

### D2:翻閱中的頁位以唯讀方式呈現

- `renderBookBlock` 依 `BOOK_BROWSE[p]` 決定要畫的兩頁(`start`、`start + 1`,超出 1–32 的位置畫 `.page-void`)。檢視的就是目前對頁時照舊用 `openPageEl`。
- 其他對頁的頁:`consumed_pages` 含該頁時畫 `cardBackEl(pg, true)`;否則畫 `cardEl(ps.book[pg - 1], {small: true})` 加上與盤面卡相同的樣式 class,點擊開純展示放大檢視(不帶 ctx,所以沒有行動按鈕),不帶選取發光。
- 魔書區加 `browsing` class,書皮旁顯示「第 N 頁」提示改為該對頁的頁碼,不另外標示,維持盤面簡潔;是否在目前頁由「回到目前頁」按鈕的亮暗表示。

### D3:按鈕位置

- 左右鍵(`‹` `›`,`aria-label` 為「前一對頁」「後一對頁」)貼在書皮左右兩緣、垂直置中,半疊在書皮外框上,不增加魔書區的寬度(寬螢幕的對角佈局與窄螢幕的直向堆疊都不受影響)。
- 「回到目前頁」為書皮上緣(對手側)或下緣(我方側)、與 MP 托盤同側的小按鈕;停用時半透明、可點時用金色強調。
- 觸控:按鈕可點範圍至少 32px。實作後以寬、窄螢幕截圖確認不遮住卡名與頁碼。

### D4:翻頁動畫與自動回到目前頁

- 收到含自己 `pages_flipped` / `pages_turned` 的批次時,在交給 `Anim.apply` 之前,若該玩家正在翻閱,先刪除翻閱項目並以前一個快照(`prevS`)重繪魔書區,讓動畫量測到的是翻動前的目前對頁,翻頁動畫才會從正確的位置開始。之後的重繪依新的 `pos` 顯示。

### D5:鍵盤

- `document` 的 `keydown`:`ArrowLeft` / `ArrowRight` / `Home` / `Escape`。
- 目標玩家:`selfPlayer()` 不為 null 時是自己;本機測試模式(`selfPlayer()` 為 null 且 `isLocal()`)是 `awaitedPlayer()`;觀戰沒有目標。目標玩家的快照沒有 `book` 時不處理。
- 不處理的情況:事件已被處理(`defaultPrevented`)、帶修飾鍵(Ctrl / Alt / Meta)、焦點在 `input` / `textarea` / `select` / `contenteditable`、對局畫面未顯示,或下列任一開著:放大檢視、決策對話框、資訊視窗、魔書網格、規則頁、金手指、意見回報。Esc 在這些情況下照舊由各視窗處理。
- 處理時 `preventDefault()`,避免捲動頁面。

### D6:i18n

新增 `ui.book.prev`(前一對頁)、`ui.book.next`(後一對頁)、`ui.book.current`(回到目前頁),加到 `zh-TW` / `en` / `ja`,簡中以 `tools/build_zh_cn.py` 產生。

## Risks / Trade-offs

- [翻閱時錯過「翻開的頁發光可選」的決策提示] → 決策提示在行動欄,且可從網格選;「回到目前頁」變亮提醒。使用者決定不在決策時自動回到目前頁。
- [按鈕擠壓窄螢幕的魔書區] → 按鈕疊在書皮邊緣,不改變尺寸;以截圖檢查。
- [Esc 與既有視窗的關閉衝突] → 視窗開著時不處理(D5)。

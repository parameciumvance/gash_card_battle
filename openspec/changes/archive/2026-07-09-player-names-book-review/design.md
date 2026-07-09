## Context

- 名稱:前端 `pname(p) = t("ui.player",{n:p+1})` 到處被呼叫(盤面、記錄、勝負、對話框標題)。房間 `Room` 有 `player_tokens`(token→index),無名稱欄位。`CreateRoom`/`JoinBody` 無 name。房間 meta(`_room_meta`)是回應中公開資訊的落點。
- 魔本檢視:`views._player_view` 只送 `open_pages`(持有者含卡片內容、他人只頁碼)、`consumed_pages`、`pos`、`book_size`,**不送完整 32 頁 book 陣列**。資訊隱藏不變量目前寫「未翻開頁內容不出現在任何回應」。`can_see_player(viewer,p)` 已是「自己/all」的單點判斷。構築器已有對頁網格(spread)排版可複用。

## Goals / Non-Goals

**Goals:**
- 暱稱端到端:輸入 → 清理 → 儲存 → meta → 前端顯示(盤面/記錄/勝負一致)。
- 己方全魔本可隨時檢視;對手/觀戰者的快照必不含己方 book。
- 引擎零改動;既有資訊隱藏測試不退步。

**Non-Goals:**
- 對戰中改名、頭像、帳號系統。
- 查閱對手魔本(違規)、棋譜回放。

## Decisions

### D1. 名稱資料流與清理

- `Room` 新增 `names: list[str | None] = [None, None]`(index=player)。公開資訊。
- `RoomStore.create(..., name=None)` 設 `names[0]`;`join(..., name=None)` 設 `names[1]`;本機房 create 以 `names: [n0, n1]` 一次帶入。
- **清理** `_clean_name(raw) -> str | None`:strip、移除控制字元、限長(16 字);清理後為空 → `None`(顯示回退預設)。清理在 API 邊界做。
- `_room_meta` 增 `names: [names[0], names[1]]`(null 表未設)。名稱非機密,全視角一致送出。

### D2. 前端名稱顯示與持久化

- `pname(p)`:`R?.names?.[p]` 有值就用,否則 `t("ui.player",{n:p+1})`。單點改寫即全站生效(盤面/log/勝負/對話框)。
- 開局面板:本機兩格暱稱、建房一格、加入一格 `<input maxlength=16>`;送出時併入 create/join body。
- localStorage 記 `gash-nick` 上次暱稱,開局面板預填。
- log 既有事件已用 `pname(ev.player)`,自動跟隨;無需改事件資料。

### D3. 己方全魔本進快照(視角化)

- `_player_view(game, p, viewer)`:當 `can_see_player(viewer, p)` 為真,附 `book: list(ps.book)`(完整 32 頁卡號);否則不含該欄。
- 語意:`book`=靜態排版順序;搭配既有 `consumed_pages`(已離開頁)、`pos`(當前對頁起點)、`used_spell_pages` 即可完整標示狀態。
- **不變量精化**:資訊隱藏規則由「未翻開頁內容不出現在任何回應」改為「未翻開頁內容 MUST NOT 出現在**對手與觀戰者**的回應;持有者本人的回應 MAY 含自己完整魔本(己方隱藏資訊,規則上本就已知)」。本機 all 視角雙方皆含(client 持雙方 token,本就全知)。

### D4. 前端查閱魔本 overlay

- 己方 `pz-head` 加「查閱魔本」按鈕(僅 `iControl(p)` 且該視角有 `book` 時顯示)。
- overlay 以對頁網格呈現 16 對頁(複用構築器 spread 概念):每頁位=頁碼+卡面;標示
  - 當前翻開對頁(`pos`, `pos+1`):高亮框;
  - 已離開頁(∈ `consumed_pages`):卡背/灰化 +「已使用/上場」;
  - 已用術頁(∈ `used_spell_pages`):角標「本回合已用」。
- 純檢視、可隨時開關、不送任何指令、不阻塞;動畫/計時不受影響。reduced-motion 無特殊處理。

### D5. 安全與驗證

- 雙視角快照測試:`snapshot(game, 對手)` 的對方 player_view **無 `book` 鍵**;`snapshot(game, "spectator")` 雙方皆無;`snapshot(game, p)` 自己有、對手無。
- 名稱清理測試:超長截斷、控制字元濾除、空字串→預設回退、XSS 字串以 textContent 呈現不執行(前端用 textContent 非 innerHTML)。
- 回歸:既有資訊隱藏測試(對手未翻開頁/翻開頁不外洩)全綠。

## Risks / Trade-offs

- [己方 book 意外流向對手] → 收斂在 `can_see_player` 單點;雙視角測試把關;本機 all 視角本就全知,無新洩露面。
- [名稱注入/XSS] → API 邊界清理 + 前端一律 textContent 渲染(現況即如此)。
- [名稱在多處顯示不一致] → 全部走 `pname()` 單點,天然一致。
- [overlay 與現有動畫/對話框層級衝突] → 獨立 overlay、純唯讀,不與 pending 決策對話框互動。

## Migration Plan

單一變更內:後端(Room.names + 清理 + meta;views 附 book)→ 前端(pname 改寫、輸入欄、overlay)→ i18n → 測試。無資料遷移;舊 client 不送 name 時 names 為 [None,None]、顯示預設,完全相容。

## Open Questions

- 查閱魔本按鈕擺放:先放己方 `pz-head`(與棄牌區並列);若嫌擠再移到動作列。
- 是否也顯示「剩餘可翻頁數/推估後續手牌節奏」等輔助資訊?先只忠實呈現 32 頁狀態,不加推算,避免過度設計。

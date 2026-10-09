## Context

動機見 proposal.md。相關現況(`frontend/app.js`):

- `cardEl(num, opts)` 是共用卡片元件:卡圖、卡名、日文名、資訊列 `.cmeta`(費用、魔力、傷害、A/D)、效果文 `.ceffect`、卡號 `.cnum`。`.cnum` 以絕對定位放在右上角(9px、淡色),壓在卡圖上;放大檢視(`#zoom-card`)把它改為卡片底部的 14px 文字;對戰盤面(`#board`)隱藏 `.cmeta`、`.ceffect`、`.cnum`。
- 卡片資料 `CARDS[num].class` 為 `none` / `intermediate` / `superior`(中級 7 張、上級 3 張),目前只有合法性檢查(`decks.js`)用到。
- 篩選 `renderCardPoolFilters(holder, filters, onChange)` 與卡池 `renderCardPool(grid, filters, onPick)`、頁位 `bookPageSlotEl(i, pages, selected, actions)` 由牌組編輯器(`B`)與金手指視窗(`CHEAT`)共用。對應魔物選單排除 `COMMAND_MAMODO`(`コマンド`);事件的 `related_mamodo` 為 null。
- 牌組編輯器中:卡池點卡 = 放入選中頁(或下一個空頁);頁位點卡 = 選取 / 再點移除 / 互換;頁位可拖拉。沒有任何路徑打開放大檢視。`zoom(num)` 不帶 ctx 時就是不帶行動按鈕的純展示檢視。
- 金手指視窗是 `<dialog>`(`showModal`,位於 top layer),一般的 `#zoom-overlay` 無法疊在它上面。

## Goals / Non-Goals

**Goals:**
- 構築時看得到卡號、中級 / 上級,篩得出指令術,選事件時不會因對應魔物篩選而落空,任何卡都能看完整詳情。

**Non-Goals:**
- 不新增「依中級 / 上級篩選」。
- 不改變卡池與頁位既有的點選、拖拉流程。
- 金手指視窗不加「詳情」按鈕。

## Decisions

### D1:中級 / 上級標籤放在資訊列

- `cardEl` 在 `.cmeta` 的內容之後加上 `<span class="cclass cclass-intermediate">中級</span>`(或上級),文字取 `card.class.intermediate` / `card.class.superior`(i18n)。
- 放在資訊列是因為它和費用、A/D 一樣是卡片的屬性:卡池、頁位(頁位隱藏效果文,但保留資訊列)、放大檢視都會顯示;盤面本來就隱藏資訊列,不必另外處理。
- 標籤加底色(中級、上級兩色),在小卡面上也能一眼看出。
- 替代方案:另外的角標。不採用:右上角給卡號、頁位左上角是頁碼,再加一個角標太擁擠。

### D2:卡號標籤

- `.cnum` 的預設樣式改為有半透明深色底的小標籤(與頁位的頁碼 `.pno` 同一種樣式),仍放在右上角、蓋在卡圖上方,字級約 10px、白字。魔本頁位放了卡時,P1 / P32 的頁碼只顯示「P1」「P32」(完整說明留在 `title` 與空頁),讓出右上角給卡號;原本的「P1 首頁(魔物)」較長,會與右上的卡號重疊。
- 放大檢視原本的樣式(卡片底部 14px 文字)與盤面的隱藏維持不變:這兩處用更具體的選擇器覆寫。
- 金手指視窗共用卡片元件,同樣會顯示新的卡號標籤。

### D3:對應魔物「無」與選事件時暫停

- 選單在「全部」之後加入 `<option value="__none__">無</option>`(`builder.filter.none`)。`renderCardPool` 的對應魔物條件改由一個函式判斷:`__none__` 時只留 `isCommandSpell(def)`;其他值照舊比對 `related_mamodo`。
- 類型為 `event` 時:選單 `disabled`,`renderCardPool` 不套用對應魔物條件;`filters.fmamodo` 不清除,切回其他類型時選單恢復可用並再次套用。
- 選單的 disabled 狀態在類型 `onchange` 時更新(類型改變時重新渲染篩選列,或直接設定選單的 `disabled`)。
- 篩選列與卡池是共用元件,金手指視窗也有同樣的行為(它的規格只寫「以類型、魔物、彈數組合篩選」,行為仍相符)。

### D4:「詳情」按鈕

- `cardEl` 新增選項 `detail: true`:在卡圖右側、卡號下方加一個小圓形按鈕(放右下角會壓到資訊列的中級 / 上級標籤)(「i」圖示,`aria-label` 為 `builder.detail`),點擊時 `stopPropagation()` 後呼叫 `zoom(num)`(不帶 ctx,為純展示檢視)。
- 牌組編輯器的 `renderCardPool` 與 `bookPageSlotEl` 由呼叫端決定是否加 `detail`:牌組編輯器加,金手指不加(它的 `<dialog>` 在 top layer,放大檢視蓋不上去)。共用函式以參數控制,不在函式內判斷呼叫端。
- 頁位的按鈕需阻止拖拉:按鈕設 `draggable=false`,且點擊不觸發頁位的選取(`stopPropagation`)。鍵盤:按鈕是 `<button>`,可 Tab 聚焦,Enter / Space 觸發;卡片本身的 Enter / Space 仍是放卡 / 選取。
- 觸控尺寸:按鈕視覺約 20px,以內距或偽元素把可點範圍擴大到約 28px,不遮住卡名。窄螢幕頁位的卡只有 72px 寬,頁碼在左上、卡號在右上、按鈕在卡號下方,不互相遮擋。
- 放大檢視在牌組編輯器中也是用 `#zoom-overlay`;點背景或關閉按鈕關閉,行為與對戰中的純展示檢視相同。
- 替代方案:點頁位的卡改為開放大檢視、在檢視中提供移除與移動。不採用:會改變既有的構築流程(使用者已選定加按鈕的方案)。

### D5:i18n

新增 `card.class.intermediate`、`card.class.superior`、`builder.filter.none`、`builder.detail`,加到 `zh-TW` / `en` / `ja`(英文沿用既有違規訊息的 Intermediate / Superior),簡中以 `tools/build_zh_cn.py` 產生。

## Risks / Trade-offs

- [小卡面上加按鈕與標籤顯得擁擠] → 卡號在右上、詳情在卡號下方的卡圖右側、中級 / 上級併入資訊列;以寬、窄螢幕截圖檢查過不互相遮擋。
- [詳情按鈕誤觸成放卡或選取] → 按鈕 `stopPropagation`,測試驗證按下後魔本與選取都不變。
- [金手指視窗的篩選行為一起改變] → 只是多了「無」與事件時暫停,與構築器一致,不影響套用流程。

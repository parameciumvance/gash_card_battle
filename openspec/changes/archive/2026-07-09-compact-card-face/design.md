## Context

`cardEl(num, opts)` 建出的卡片結構:`img.art` → `.cname` → `.cname-ja` → `.cmeta`(費用/魔力/傷害/AD)→ `.ceffect` → `.cnum` → 徽章 → `.btns`。盤面卡片固定 104×150、`overflow:hidden`,`#board .card` 已隱藏 `.ceffect`、`.cname-ja`;`.btns` 為 `margin-top:auto` 沉底。art 現為 75px。放大檢視 `#zoom-card .card` 顯示全部(cmeta/ceffect 可見),點卡片即觸發 `zoom(num)`(按鈕 `stopPropagation`)。

問題:art(75)+ 卡名(可 2 行)+ cmeta(1–2 行)+ 徽章 + 按鈕列(可多個)超過 150px,`overflow:hidden` 從底部裁掉按鈕列。

## Goals / Non-Goals

**Goals:**
- 盤面卡面只以卡名為主(+卡圖+狀態+按鈕);數值/效果不佔盤面空間。
- 行動按鈕在任何按鈕數量下都不被裁切。
- 完整資訊在點卡放大時呈現(既有路徑)。

**Non-Goals:**
- 放大檢視內容改動、構築器卡片呈現、卡片元件重寫。
- 新增額外「詳情」按鈕(點卡放大已足夠)。

## Decisions

### D1. 盤面隱藏數值列,保留卡名

- `#board .card .cmeta { display: none }`(比照既有 `.ceffect`/`.cname-ja` 隱藏)。盤面卡面剩:art、cname、徽章、btns。
- 以 CSS 為主、零 JS 邏輯改動(cardEl 仍照常建 cmeta,只是盤面情境以 CSS 隱藏)——降低風險、放大檢視與對話框不受影響。

### D2. 版面保證按鈕可見

- 卡名 `.cname` 於盤面限高(如 2 行 `-webkit-line-clamp:2` + 省略號),避免長名把按鈕擠出。
- 盤面 art 維持 75px(實測:光是隱藏 cmeta/效果/日文名/卡號,art 75 + 卡名 2 行 + 徽章 + 按鈕總高即 ≤ 150,不需縮 art)。卡片仍固定 150px、`overflow:hidden` 保留。
- `.btns` 維持沉底;以 E2E 量測按鈕底緣 ≤ 卡片底緣驗證不裁切。

### D3. 適用範圍

- 僅 `#board .card`(魔物、搭檔、魔本頁、對決舞台若有卡片)套用精簡;`#zoom-card`、構築器(`#pool-grid`/`#book-grid` 的 `.page-slot .card`)不受此規則影響(構築時需要看數值,維持既有)。
- 選書/棄牌對話框(`#dialog-options .card`)沿用既有呈現(這些是小卡列表,不受盤面固定高度限制),不在本次調整。

## Risks / Trade-offs

- [看不到費用/魔力導致決策不便] → 費用不足時按鈕本就 disabled 並顯示「MP < N」原因;完整數值點卡即見。可接受,且符合使用者明確取捨(卡名以外點細節再看)。
- [卡名過長被截斷] → 2 行省略號 + 放大檢視看全名;盤面以辨識為主。
- [不同按鈕數量的高度] → 以最壞情況(2 按鈕 + 徽章)量測;E2E 斷言按鈕不裁切。

## Migration Plan

純 CSS(必要時 cardEl 加一個 `.cmeta` 已存在無須改)。單一變更內:調整 `#board .card` 規則 → E2E 量測按鈕可見 → 截圖抽查。無資料/API/行為變更。

## Open Questions

- 是否在盤面保留一個極小的費用角標(折衷:名字為主但留費用)?先依使用者要求完全移除數值、只留卡名;實測若覺得費用還是常看,再加角標。

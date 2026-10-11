## Context

- 快照的魔物槽有 `stack`(由下而上,最後一張是頂層),對所有視角公開。
- 盤面只顯示頂層與 `×N` 標記;放大檢視 `renderZoom` 以 `ZOOM = {num, ctx}` 呈現單張卡與行動按鈕,魔物槽的 ctx 為 `{kind: "slot", p, uid}`。

## Goals / Non-Goals

**Goals:** 放大檢視中確認疊放在下方的卡。

**Non-Goals:** 不改盤面版面(維持 `×N`);不改伺服器。

## Decisions

### D1:放大檢視中的疊放區

- `renderZoom` 在 ctx 為魔物槽、`stack.length > 1` 時,於行動區上方加 `.zoom-stack`:標題「疊放在下方」與 `stack` 除頂層外由上而下的小卡(`cardEl(num, {small: true})`)。
- 點小卡:`ZOOM = {num, ctx: null, back: 原本的 ZOOM}`,純展示;`back` 存在時行動區加「返回」按鈕,回到原本的魔物。
- 原魔物已離場時,原本的 `gone` 判斷照常關閉檢視;純展示的下方卡沒有 ctx,不受影響。

## Risks / Trade-offs

- [下方卡片多時佔空間] → 疊放最多 2–3 張,小卡橫排即可。

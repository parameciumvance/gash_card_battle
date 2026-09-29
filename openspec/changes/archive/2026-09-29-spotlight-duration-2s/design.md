## Context

- 停留時間集中在 `anim.js` 的 `spotlightMs`:標準 1000ms、快 500ms,只有 pass 的格為一半;排隊 ≥ 2 批時自動用快。
- NPC 送出前的等待(`NPC_QUIET_DELAY` / `NPC_ACTION_DELAY`)刻意略長於標準聚焦,畫面才跟得上 NPC。

## Goals / Non-Goals

**Goals:** 標準停留 2 秒,其餘比例關係不變。

**Non-Goals:** 改變追趕的門檻或聚焦的內容。

## Decisions

- 標準 2000ms、快 1000ms;只有 pass 的格為一半(1000ms / 500ms)。「快」與 pass 仍以「一半」推得,只改基準值。
- NPC 等待:pass 類 1.2 秒(略長於 pass 的 1 秒)、其他 2.3 秒(略長於 2 秒)。

## Risks / Trade-offs

- [NPC 回合變慢(每個行動約 2.3 秒)] → 玩家可在演出設定改「快」或「關」;NPC 的等待是固定值,不隨玩家設定改變,改「快」時畫面只是比 NPC 先播完。
- [線上計時:聚焦時間計入回合計時] → 2 秒對 30 秒計時仍有限;可改「快」。

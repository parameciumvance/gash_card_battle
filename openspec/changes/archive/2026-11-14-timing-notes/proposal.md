## Why

todo 的「芭莉盾翻頁時機、S-104 檢視時機、古蘭庫時機」三項,explore 後確認程式都正確,只有文件需要整理(使用者 2026-11-14 要求開小 change 結案):

- 芭莉盾 = S-106 ゾルシルド:2026-11-08 的 defense-effects-timing 已把無效與翻自己 1 頁延後到「効果の使用」的最後(spec 與 design「防禦戰術的效果…」一致),但 card-effects design 第三彈第 3 批的段落仍寫「S-106 宣告時無效並翻自己 1 頁」,是漏改的舊說明。卡頁(pages/1118)沒有 FAQ。
- S-104 ギガノ・ゾニス:現行在攻擊成功時、套用傷害前檢視,和卡頁(pages/1120)FAQ A1 一致;design 只寫「使用者確認」,補上 FAQ 原文作為依據。
- 古蘭庫 = S-068 グランクラッグ:宣告時擲幣、本場戰鬥結束後起禁戰術,spec、design、程式一致(2026-10-17 使用者指正);卡頁(pages/1166)沒有 FAQ。不需修改。

## What Changes

- 只改 `openspec/specs/card-effects/design.md`:修正 S-106 的舊說明;S-104 補 FAQ 依據。程式與規格不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

(無規格變更;只更新 `card-effects` 的 design)

## Impact

- `openspec/specs/card-effects/design.md`。

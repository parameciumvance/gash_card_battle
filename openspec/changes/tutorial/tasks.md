# Tasks

## 1. 測試先行

- [x] 1.1 API 測試:建立教學房(玩家先攻、局面、不計時、沒有金手指、反面硬幣);`tutorial/continue` 的權限與效果(對手在放行前不出手);關閉教學房。
- [x] 1.2 劇本測試:以 API 依劇本走完 17 步,斷言每步的關鍵結果(第 6 步對手不能防禦、第 10 步 8000 對 6000 攻擊無效、第 11 步擲反面、第 16 步 7000 對 6000);第 11 步保護 / 不保護三種分支都能走完;自由步驟提早 pass 仍能走完。
- [x] 1.3 瀏覽器測試:首頁入口與順序;教學面板逐步顯示;鎖定時指令不送出並提示;對手在「下一步」前不行動;離開回首頁且不在返回清單;完成後的按鈕與已完成標示;四語 key 一致。走完全程的測試標 `slow`。

## 2. 後端

- [x] 2.1 `data/tutorial/` 雙方魔書;`MODES` 加 `tutorial`;建房、先攻、反面 RNG(D1)。
- [x] 2.2 `src/gash/tutorial/` 對手腳本與 `_npc_decide` 分派(D2)。
- [x] 2.3 `tutorial_hold` 與 `tutorial/continue` 端點(D3);`close_room` 原本就允許非 online 模式(D5)。

## 3. 前端

- [x] 3.1 首頁「教學」入口(含已完成標示)與開始。
- [x] 3.2 教學面板、步驟表、鎖定(`send()` 攔截)、目標發光、對手節奏(D4)。
- [x] 3.3 離開與完成流程(D5)。
- [x] 3.4 四語文字(D6)。

## 4. 驗證與文件

- [x] 4.1 快速測試組(2053)、相關瀏覽器測試(首頁、牌桌、自動 pass、棄權、返回清單、NPC、記錄,共 56 項,含走完全程的 slow 測試);桌面與手機寬度截圖確認(手機上目標被面板蓋住,已改為換步驟時捲到中央、面板可收合)。
- [x] 4.2 新增 `openspec/specs/tutorial/`(spec 與 design),更新 `capability-map.md`(新 capability、與 online-room / npc-opponent / battle-ui 的關係);`battle-ui` design 補首頁入口。
- [ ] 4.3 `openspec validate tutorial --strict`;使用者確認。

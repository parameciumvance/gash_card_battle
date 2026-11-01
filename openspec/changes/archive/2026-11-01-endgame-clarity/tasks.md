# Tasks

## 1. 測試先行

- [x] 1.1 引擎測試:魔書翻開到最後一頁(第 32 頁)的回合玩家在結束階段敗北,MP 不變、沒有 `pages_flipped`;有 M-030 待命時不敗北。執行並確認修改前失敗(MP/事件那項)
- [x] 1.2 快照測試:`end_flip_loses` 對回合玩家/對手、有 `skip_end_flip` 待命、還有頁可翻、對局結束後。確認修改前失敗
- [x] 1.3 瀏覽器測試:魔書耗盡的進度顯示、敗方視角的原因文字、最後一對頁警示與 Pass 說明(含對手在最後一對頁時不顯示)、結算面板(NPC 落敗內容、再戰、關閉後重開、本機測試、牌桌按鈕在面板內)、新訪客不跳更新公告。確認修改前失敗

## 2. 引擎與快照

- [x] 2.1 結束階段無頁可翻直接敗北(D1),判定抽成共用函式
- [x] 2.2 `end_flip_loses` 玩家快照(D2)

## 3. 前端

- [x] 3.1 魔書耗盡顯示(D4)與勝負原因點名敗方(D5),四語
- [x] 3.2 最後一對頁警示與 Pass 說明(D3),四語
- [x] 3.3 結算面板與再戰/再來一場/返回首頁,牌桌按鈕移入(D6),四語
- [x] 3.4 新訪客不跳更新公告(D7)
- [x] 3.5 修正受影響的既有測試(牌桌結束按鈕改在結算面板內找、更新公告測試預設為確認過舊版的訪客)
- [x] 3.6 牌桌對方離開、自己成為開桌者進入等待畫面時,結算面板沒關且舊的終局快照讓它再次跳出,擋住等待畫面(`test_opponent_leaves_and_i_host` 抓到):離開對局畫面時關閉、只在對局畫面跳出

## 4. 驗證

- [x] 4.1 快速測試組(1503 passed)與相關瀏覽器測試(endgame-clarity、release-notes、tables、npc、turn-dial、timing、feedback、battle-info、peek、language、npc-room、log-reset、resume-room、sound、i18n、spotlight 共 198 passed)通過;寬/窄螢幕中英截圖確認面板與警示(無橫向捲動,修正了「魔書 魔書耗盡」前綴重複與英文「1 turns」);`openspec validate endgame-clarity --strict` 通過,主 spec 驗證與警告數與基準相同
- [x] 4.2 本機實際操作抽查(使用者)

## 5. Reconciliation(指南 §13)

- [x] 5.1 同步 game-engine、battle-api、battle-ui 主 spec
- [x] 5.2 更新受影響 capability 的 `design.md`(結算面板、警示、強制翻頁判定)與 capability map

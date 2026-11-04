# Tasks

- [x] 1.1 瀏覽器測試:同一個瀏覽器兩個分頁分別開房與加入,各自重新整理後身分不變;新分頁開房間連結時用瀏覽器記得的身分。修改前 A 重新整理後變成 B(viewer 1),測試失敗
- [x] 1.2 `saveSession` / `loadSession` 改為分頁身分優先(D1),`leaveRoom` 清除
- [x] 1.3 快速測試組(1520 passed)、全部非 slow 瀏覽器測試(372 passed)與 NPC / 接回房間測試通過;`openspec validate fix-session-identity --strict`
- [x] 1.4 本機實際操作抽查(使用者)
- [x] 1.5 同步 battle-ui 主 spec 與 design

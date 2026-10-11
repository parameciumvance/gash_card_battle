## Context

- 部署時卡圖目錄 `/app/assets` 是 volume(`GASH_ASSETS_DIR`),伺服器重啟會讓對局消失;`/api/meta` 每次請求即時檢查卡圖目錄。
- 頂欄在所有畫面都有;「更新內容」是新版上線後才跳出的對話框。

## Goals / Non-Goals

**Goals:** 不重啟就能發布 / 撤下公告;所有畫面(含對局中)都看得到。

**Non-Goals:** 管理介面或發布 API;WebSocket 即時推送;維護前擋住新房間(使用者決定先不做);排程開始時間。

## Decisions

### D1:公告檔與端點

- 位置:`resolve_assets().dir / "announcement.json"`。放在既有的 volume,不新增設定;用 `docker compose cp` 或 `exec` 寫入即可。
- `GET /api/announcement` 每次讀檔:`id`(字串)、`message`(語言 → 文字的物件,至少一項)、`until`(可選,ISO 8601,含時區;沒有時區視為 UTC)。不合格一律回傳 null,並記錄警告,不讓請求失敗。
- 獨立端點,不併入 `/api/meta`:`/api/meta` 的規格限定欄位,且公告需要定期查詢,端點保持輕量。

### D2:前端橫幅

- `#announcement` 放在頂欄下方,所有畫面共用;訊息以 `textContent` 呈現。
- `refreshAnnouncement()`:啟動時與每 120 秒呼叫;失敗時不改目前狀態。
- 關閉:`localStorage` 的 `gash-announcement-dismissed` 記關閉的 `id`(只記最後一則,新的 `id` 自然再顯示)。

## Risks / Trade-offs

- [最多晚 2 分鐘看到] → 維護公告通常提前發布,可接受。
- [編輯檔案時讀到寫了一半的內容] → 格式錯誤視為沒有公告,下一次查詢就正確;README 建議先寫到暫存檔再搬移。

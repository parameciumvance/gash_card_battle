# Tasks

## 1. 公告驗證共用函式

- [x] 1.1 新增 `src/gash/announcement.py`:`parse_announcement`(原因代碼 `json` / `id` / `message` / `until` / `expired`)與 `announcement_warnings`(缺語言、佔位文字、與 `zh-TW` 相同、`until` 沒有時區),語言取自 `frontend/i18n/languages.json`。單元測試 `tests/test_announcement_rules.py` 涵蓋每個原因代碼與每種提醒(含 10/12 那則:`zh-CN` 為 `"123"`、`en` / `ja` 為 `"..."`),並確認合格的公告沒有提醒
- [x] 1.2 `read_announcement` 改用 `parse_announcement`,過期靜默、其他原因記警告;既有 `tests/test_announcement.py` 不改且全數通過

## 2. 維運腳本 `tools/vps.py`

- [x] 2.1 連線層:`Remote`(`GASH_VPS` / `GASH_VPS_DIR`、`shlex.quote`、ssh 失敗時非 0 結束並顯示 stderr)與公開網址查詢(`GASH_PUBLIC_URL`)。測試:環境變數覆蓋目標與目錄、組出的遠端命令正確引用、ssh 失敗時非 0 且不顯示成功訊息
- [x] 2.2 `cards`:列出遠端卡圖、比對、只打包缺的(擁有者 1000:1000)、`--force <卡號>`、已同步時不上傳、上傳後回報總數。測試以假的 `Remote` 驗證 tar 內容只含缺的卡、`--force` 的卡一併上傳、已同步時沒有上傳呼叫
- [x] 2.3 `announce FILE`:驗證擋下時非 0 且沒有上傳呼叫;列出訊息與提醒後詢問,回答否不上傳,`--yes` 直接上傳;上傳的遠端命令為同目錄暫存檔 + `mv`;以公開 API 確認 `id`,不一致或連不上時非 0 並顯示實際回應。測試覆蓋以上每個分支
- [x] 2.4 `announce --clear`:刪除並確認為 null;沒有公告時說明並正常結束。測試覆蓋兩個分支
- [x] 2.5 `status`:顯示 `/api/meta` 版本、compose 服務狀態、遠端與本機卡圖張數、目前公告;只呼叫唯讀的遠端命令(測試檢查沒有寫入類命令)

## 3. 文件與實機確認

- [x] 3.1 README「卡圖」「維護公告」改以腳本為主、手動指令留作備案;`docker-deployment` design 新增「維運腳本」一節(連線、串流、共用驗證的理由)。確認 README 中的指令與腳本的實際參數一致(`python tools/vps.py --help`)
- [x] 3.2 對正式站實際執行 `status` 與 `cards`(預期已同步、不上傳);公告的發布 / 撤下由使用者決定是否實測(會短暫顯示給玩家)。結果:status 顯示 v1.3.3、三個容器正常、VPS 332 張 / 本機 135 張、沒有公告;cards 回報已同步、未上傳;以 VPS 上 10/12 的公告檔試跑 announce,已過期被擋下,改成未來時間後提醒 zh-CN / en / ja 像佔位文字,回答否未上傳;之後實際發布測試公告 test-20261106-0537(四語「公告測試」,until 15 分鐘後),腳本確認生效、使用者在網站上看到橫幅、VPS 上沒有留下 .tmp,再以 --clear 撤下並確認線上沒有公告;沒有公告時再撤下回報不需要撤下
- [x] 3.3 `python -m pytest tests -m "not slow and not browser" -q` 與 `tests/test_announcement_ui.py` 通過;`openspec validate vps-ops-script --strict` 通過(1569 passed、9 skipped;公告 UI 3 passed)

## Workflow follow-up

- 歸檔前依指南 §13 reconciliation:同步 `docker-deployment` delta spec,主 spec 的 Purpose / Scope 加上「維運腳本」;`battle-api` design 記一筆公告驗證改由共用函式實作;capability map 的 `docker-deployment` 責任欄補上維運腳本。

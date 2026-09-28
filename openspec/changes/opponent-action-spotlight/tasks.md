## 1. 推送標明行動者

- [x] 1.1 先寫測試(`battle-api`「推送標明行動者」三個情境:玩家指令、NPC 與逾時代打、金手指),確認修改前失敗
- [x] 1.2 `_broadcast` 與指令回應帶 `actor`(design D1)

## 2. 演出設定與動畫開關

- [x] 2.1 頂欄「演出」面板:聚焦(標準 / 快 / 關)、動畫(開 / 關 / 跟隨系統),存 localStorage,i18n
- [x] 2.2 `anim.js` 的動畫開關改讀設定,未設定時依 `prefers-reduced-motion`(design D4)
- [x] 2.3 既有瀏覽器測試的 fixture 預設關閉聚焦(design D6)

## 3. 聚焦展示

- [x] 3.1 事件分類表(卡片類 / 文字類 / 不聚焦)與「要不要聚焦」的判斷(design D2)
- [x] 3.2 時間軸組成:卡片格、結果行併入、擲硬幣 / 魔力對決前後分格;聚焦遮罩、點擊跳過、逾時保底、動畫關時無淡入淡出
- [x] 3.3 追趕與背景分頁(design D3)
- [x] 3.4 `app.js` 把 `actor` 傳進 `Anim.apply`(指令回應與推送)
- [x] 3.5 瀏覽器測試:`battle-ui`「對手行動聚焦展示」「演出設定」各情境,以及「事件動畫」的遊戲內關閉動畫

## 4. NPC 節奏

- [x] 4.1 NPC 等待秒數調整(design D5),更新 `online-room/design.md` 的說明

## 5. Reconciliation 與歸檔(指南 §13)

- [ ] 5.1 同步 delta spec 回 `battle-ui`、`battle-api` 主 spec
- [ ] 5.2 Reconcile affected capability design and rationale:`battle-api/design.md` 補 `actor`;`online-room/design.md` 的 NPC 等待秒數;`battle-ui` 尚無 design.md,聚焦的分類表與時間軸寫在新建的 `battle-ui/design.md`
- [ ] 5.3 Update capability map:`battle-ui` 的 design 覆蓋改為 Partial
- [ ] 5.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

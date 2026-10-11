## Context

- S-043 分裂是兩個連續的 `Choose(OwnBookCopiesOf("M-024"), then=PlayMamodoFromBook())`;`Choose` 單一選項自動解決,所以剛好 2 張時第二張自動放出。
- 魔書網格 `showBookReview` 的標題是「查閱魔書」或「X 的魔書」;棄牌區 `showDiscard` 用 `showDialog`,它已支援 `sourceNum`(來源卡名與效果文)與 `notes`。決策提示在行動欄,網格開啟時被蓋住。

## Goals / Non-Goals

**Goals:** S-043 分裂兩張都由玩家選;選擇畫面顯示要選什麼。

**Non-Goals:** 不做一次選多張(使用者決定:依實體操作一張一張來);不顯示「第幾張」的進度(引擎的決策沒有這個資訊,兩次選擇的標題相同)。

## Decisions

### D1:S-043 第二次選擇 `auto_single=False`

第一次選擇一定至少 2 個選項(使用條件要求魔書至少 2 張),只有第二次可能剩一張,所以只在第二次加。合體選 M-025 維持自動(M-025 每副魔書最多 1 張,不是玩家的選擇)。

### D2:選擇提示

- 共用 `pickHint(p, zone)`:目前的決策(`PICK`)在該玩家的魔書 / 棄牌區有目標時,回傳決策的通用標題(`choice.title.<kind>`)與來源卡號;否則 null。
- 魔書網格:標題下加 `#book-review-hint`,顯示「標題 — 來源:卡名」,沒有提示時隱藏。
- 棄牌區:`showDialog` 帶 `notes=[標題]` 與 `sourceNum=來源卡`,沿用既有的來源卡區塊。
- 檢視對手魔書沒有可選的卡(`end_book_review`)時,標題本來就寫明「沒有可選的卡」,也顯示提示(其通用標題「檢視對手的魔書」)。

### D3:自動開啟等疊加演出播完

使用者發現:S-043 選了第一張,還沒看到它飛上場,第二次選擇的網格就蓋上來。疊加式動畫(飛卡、棄牌)在重繪後播放、不阻塞,`autoOpenPick` 卻在重繪後立刻執行。`Anim.overlaySettleMs(events)` 依這批事件估計疊加演出的長度(放卡 480ms、棄牌 600ms;動畫關閉為 0),`applyPayload` 等這段時間後才自動開啟。同一批事件經 HTTP 回應與 WS 推送各到一次,第二次因 `seq` 去重沒有新事件、估計為 0,會立刻開啟(使用者回報仍蓋住飛卡);所以改記「最早可開啟的時間」`pickOpenNotBefore`,任何觸發都等到那時。

### D4:棄牌飛向棄牌區

- 量測(重繪前):`mamodo_discarded` 用魔物槽;`card_discarded` 依 `zone` 找搭檔欄 / 魔物欄(以新增的 `slot` 欄位)或魔書翻開的頁,魔書看不到的頁用魔書封面。
- 重繪後以 `cardEl` 建立該卡的複製品,自起點縮小、旋轉、淡出飛向該玩家區塊標頭的「棄牌區」(`.discard-btn`),600ms。取代原本魔物原位淡出的 `fx-discard`。
- 引擎的 `card_discarded` 加 `slot`(搭檔以代價棄掉、隨魔物送墓、效果棄掉、疊放頂層入墓),是公開資訊。

### D5:CSS 自訂屬性的設定

`Object.assign(el.style, {"--fly-ms": …})` 不會設定自訂屬性(只有 `style.setProperty` 可以),轉場時間因此無效:傷害能量、命中爆光、保護移動、棄牌在先前的實作都是瞬移。全部改用 `setProperty`。截圖檢查時發現:headless 瀏覽器重繪後主執行緒忙約 250ms,轉場起步會被延後,這是測試環境的效能問題,實際瀏覽器不受影響。

## Risks / Trade-offs

- [兩次選擇標題相同,看不出是第幾張] → 第一張放出後場上已看得到,可接受;若需要再由引擎在決策中帶進度。

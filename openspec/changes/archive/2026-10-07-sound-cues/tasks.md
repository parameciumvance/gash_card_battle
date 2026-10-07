## 1. 先寫測試

- [x] 1.1 瀏覽器測試(`tests/test_sound_ui.py`,以 `Sfx.played` 驗證):對手宣告攻擊在聚焦時播放 `attack`;自己放卡播放 `card`;同批傷害與翻頁只播 `damage`;行動權轉到自己播放 `your_turn`、本機模式不播;勝負分別為 `win` / `lose`;音效關閉時不播放;音效設定被記住且缺省為開。確認修改前失敗

## 2. 實作

- [x] 2.1 `frontend/sound.js`:音效合成、`CUES` 對照與優先順序、使用者互動後啟用 `AudioContext`(design D1、D2)
- [x] 2.2 `anim.js`:時間軸各格記錄事件,依格 / 演出 / 重繪的時間點播放;重繪後判斷「輪到你」(design D3、D4)
- [x] 2.3 `app.js`:`awaitedPlayer(state)`、演出設定加入音效;`index.html` 載入 `sound.js`;四種語言 i18n(簡中以 `tools/build_zh_cn.py` 產生)(design D5)
- [x] 2.4 使用者實際在瀏覽器聽過各音效(自動測試只驗證決定播放的音效與合成不報錯)

## 3. Reconciliation 與歸檔(指南 §13;主 spec 已手動同步,歸檔用 `--skip-specs`)

- [x] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 新增「音效」一節,「演出設定」補 `gash-sound`
- [x] 3.3 capability map 的 `battle-ui` 責任補上音效
- [x] 3.4 `openspec validate --all --strict`、相關測試全過後歸檔

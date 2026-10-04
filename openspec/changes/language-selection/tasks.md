## 1. 先寫測試

- [ ] 1.1 6 處 `new_context` 加上 `locale="zh-TW"`,確認既有測試照常通過
- [ ] 1.2 靜態測試(design D9):三種字典條目與參數一致;規則頁三種語言段落 id 與順序一致、不提不存在的機制(依語言);卡片文字檔涵蓋全部卡號、`name_ja` 與 `cards_ja.csv` 一致、`cards.ja.json` 可由工具重新產生且相同、英文 `name` / `attr` 與 TTS 卡表一致、英文 `effect` 不含假名;每個伺服器錯誤碼在三種字典都有 `error.<code>`
- [ ] 1.3 瀏覽器測試(`battle-ui`「語言選擇」「錯誤訊息依錯誤碼顯示」「i18n 字典」、`battle-api`「預組魔本探索」、`deck-builder`「即時合法性提示」):依瀏覽器語言決定預設(ja、fr → en)、選擇後記住、對局中切換後接回且記錄為新語言、同房不同語言、錯誤訊息依語言、預組名稱依語言、日文卡名與小字、構築器違規訊息依語言;確認修改前失敗

## 2. 語言基礎

- [ ] 2.1 `frontend/i18n/languages.json`;語言偵測與 `gash-lang`(design D1)
- [ ] 2.2 `boot()` 依語言載入字典、規則頁、卡片文字;`ZH` 改名 `TEXT`;載入失敗退回 `zh-TW`;`<html lang>` 與日文字型(design D2)
- [ ] 2.3 頂欄 `#lang-toggle` 與語言對話框,選擇後記住並重新載入(design D3)
- [ ] 2.4 卡名格式 `ui.card_with_attr`、卡名下方小字依語言、「(你)」改走字典(design D5)
- [ ] 2.5 錯誤碼對應 `error.<code>`(design D6);中文字典補全部錯誤碼
- [ ] 2.6 `/api/decks` 回傳 `name_key`,前端依語言解析;三種字典補 `deck.level1`、`deck.level2`(design D7)

## 3. 日文

- [ ] 3.1 `tools/build_card_texts.py` 產生 `data/cards.ja.json`(design D4)
- [ ] 3.2 `frontend/i18n/ja.json`(全部條目,規則書用語,design D8)
- [ ] 3.3 `frontend/i18n/rules.ja.json`

## 4. 英文

- [ ] 4.1 `data/cards.en.json`:名稱與效果名由工具自 TTS 卡表寫入;135 張效果依 `effect_ja` 翻譯(design D4)
- [ ] 4.2 `frontend/i18n/en.json`(全部條目,卡圖用語,design D8)
- [ ] 4.3 `frontend/i18n/rules.en.json`

## 5. 檢查與文件

- [ ] 5.1 截圖確認三種語言的首頁、設定頁、對局、行動欄、對話框、規則頁、構築器(桌面與手機)
- [ ] 5.2 README:語言切換、日英為初版翻譯尚未經母語者校對、英文效果文依日文翻譯而與卡圖不同

## 6. Reconciliation 與歸檔(指南 §13)

- [ ] 6.1 同步 delta spec 回 `battle-ui`、`deck-builder`、`card-data`、`battle-api` 主 spec;`battle-ui` Purpose 的「中文介面」改為三種語言
- [ ] 6.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補「語言」(載入、切換以重新載入、錯誤碼、卡名格式、用語);`card-data` 記錄卡片文字檔的產生方式與英文翻譯依據
- [ ] 6.3 Update capability map(`battle-ui` 的 i18n 改為三種語言;`card-data` 責任補上日英卡片文字)
- [ ] 6.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

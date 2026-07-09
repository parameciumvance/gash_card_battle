# battle-api — 差分:預組探索端點與具名預組解析

新增預組探索端點,並把預組解析由「只認 level1」一般化為「依 id 載入掃描集合內的具名預組」。

## ADDED Requirements

### Requirement: 預組魔本探索
API SHALL 提供 `GET /api/decks` 端點,回傳伺服器 `data/decks/` 目錄下所有預組魔本的清單(每項含 `id` 與顯示名 `name`)。顯示名 SHALL 依牌組 JSON 解析:有 `name_key` 則經 i18n 字典解析,否則用內嵌 `name`,再無則退回 `id`。清單 SHALL 於啟動時掃描並可快取;無法解析為合法牌組的檔案 MUST 被排除而不使端點失敗。

#### Scenario: 列出預組
- **WHEN** 前端請求 `GET /api/decks`
- **THEN** 回應含至少 level1 一項,每項有 `id` 與可顯示的 `name`

#### Scenario: 丟檔即現
- **WHEN** 開發者於 `data/decks/` 放入一個合法的新預組 JSON 並重啟伺服器
- **THEN** 該預組出現在 `GET /api/decks` 回應中,無需其他程式碼改動

## MODIFIED Requirements

### Requirement: 建立對局
對局 SHALL 經由房間流程建立(見 `online-room`):線上房於雙方到齊時、本機房於建房時,載入預組魔本、初始化引擎(可選指定 RNG seed)、執行準備階段。牌組欄位 SHALL 解析為下列之一:`{preset: id}` 依 id 自掃描集合載入對應預組(id MUST 限縮在掃描到的集合,絕不轉為任意檔案路徑;未知 id 回 4xx);`{pages:[...]}` 自訂牌組以構築規則驗證(違規回 422);缺省(無牌組欄位或 `{preset:"level1"}`)為預設預組 level1。直接建立無主對局的舊端點 MUST 移除。

#### Scenario: 開局初始狀態
- **WHEN** 房間雙方到齊而建立對局
- **THEN** 狀態為先攻玩家的開始階段,雙方 MP 2、首頁魔物已在場

#### Scenario: 指定具名預組開局
- **WHEN** 建房或加入請求帶 `{preset: "<掃描到的預組 id>"}`
- **THEN** 開局後該方魔本為對應預組內容

#### Scenario: 未知預組被拒
- **WHEN** 請求帶 `{preset: "../../etc/passwd"}` 或任何不在掃描集合中的 id
- **THEN** 回應 4xx 與原因碼,不讀取任何非預組檔案,對局不建立

#### Scenario: 自訂牌組仍驗證
- **WHEN** 請求帶 `{pages:[...]}` 且違反構築規則
- **THEN** 回應 422 與構築規則原因碼

# battle-api — 後端對局 API

## Purpose

FastAPI 薄殼:對局生命週期、指令轉發、狀態快照。引擎為唯一規則權威。

## Requirements

### Requirement: 建立對局
API SHALL 提供建立新對局的端點:載入預組魔本(雙方共用 level1.json)、初始化引擎(可選指定 RNG seed)、執行準備階段,回傳對局 ID 與初始狀態快照。

#### Scenario: 建立對局
- **WHEN** 客戶端 POST 建立對局
- **THEN** 回傳對局 ID,狀態為先攻玩家的開始階段,雙方 MP 2、首頁魔物已在場

### Requirement: 指令提交
API SHALL 提供指令提交端點:接受帶 `player` 欄位的指令 JSON,轉交引擎;回傳引擎結果(成功=新狀態摘要+本次事件列表;失敗=原因碼)。指令 MUST 逐一循序處理,同一對局不併發。

#### Scenario: 提交合法指令
- **WHEN** 客戶端提交回合玩家的翻頁指令
- **THEN** 回應含 PagesFlipped/MPChanged 事件與更新後狀態

#### Scenario: 提交非法指令
- **WHEN** 客戶端提交時機不符的指令
- **THEN** 回應 4xx 與引擎原因碼,對局狀態不變

### Requirement: 狀態快照與資訊隱藏
狀態查詢端點 SHALL 回傳渲染所需完整狀態(階段、行動權、雙方 MP、場面、當前對頁與已翻開頁、戰鬥子狀態、pending choice、累積事件 log);魔本**未翻開頁面的內容 MUST NOT 出現在任何 API 回應中**。

#### Scenario: 未翻頁內容不外洩
- **WHEN** 客戶端查詢狀態時任一玩家魔本尚有未翻開頁
- **THEN** 回應中未翻開頁僅以頁碼/張數表示,不含卡片內容

#### Scenario: 快照可完整重繪
- **WHEN** 前端重新整理後以對局 ID 查詢狀態
- **THEN** 回應足以完整重建畫面(含行動 log),無需重放指令

### Requirement: 事件記錄
對局 SHALL 累積自開局以來的全部事件(含序號);API MUST 支援自指定序號起增量取得事件,作為行動 log 與未來線上同步的基礎。

#### Scenario: 增量取得事件
- **WHEN** 客戶端以上次已知序號查詢事件
- **THEN** 僅回傳其後發生的事件,序號連續

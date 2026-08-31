# battle-ui — 對戰介面

靜態 HTML + 原生 JS(ES modules),由 FastAPI serve;中文介面,hotseat 雙人共用畫面。

## ADDED Requirements

### Requirement: i18n 字典
UI 的所有顯示文字 SHALL 取自 `i18n/zh-TW.json` key-value 字典(含參數模板),程式碼中 MUST NOT 硬編任何顯示用中文字串;卡片文本取自 `data/cards.zh-TW.json`。新增語言 SHALL 只需新增字典檔。

#### Scenario: 文字全走字典
- **WHEN** 檢查前端程式碼
- **THEN** 顯示文字均經 t(key, params) 取得,無硬編中文字串

### Requirement: 盤面呈現
UI SHALL 呈現:雙方魔本當前對頁(頁上卡片=可用手牌)、雙方場區(魔物及所裝夥伴、健康直放/負傷橫放)、雙方 MP、當前階段與行動權指示、戰鬥子狀態(攻防宣告內容、合計魔力)。

#### Scenario: 負傷魔物橫放顯示
- **WHEN** 場上魔物進入負傷狀態
- **THEN** 該卡以橫放(旋轉)樣式呈現

#### Scenario: 戰鬥中顯示合計魔力
- **WHEN** 攻防雙方皆已宣告
- **THEN** 畫面顯示雙方當前合計魔力(含 modifier)並隨戰鬥中效果即時更新

### Requirement: 卡圖與文字卡面
卡片元件 SHALL 一律先渲染文字卡面(卡名、費用、A/D、魔力、傷害、效果文中譯);對應卡圖檔存在時 SHALL 疊加顯示,並提供懸停/點擊放大檢視完整卡片資訊。

#### Scenario: 卡圖缺失時可玩
- **WHEN** 某卡無卡圖檔
- **THEN** 該卡以文字卡面正常顯示與操作,不出現破圖

### Requirement: 行動記錄
UI SHALL 將事件流以 i18n 模板渲染為中文行動記錄,依時間序顯示並自動捲動;記錄 MUST 涵蓋翻頁、MP 變化、放卡、效果啟動、硬幣結果、戰鬥結果、傷害與勝敗。

#### Scenario: 事件渲染為中文記錄
- **WHEN** 發生 CoinFlipped(正面)事件
- **THEN** 記錄區出現如「擲硬幣:正面」的中文條目

### Requirement: 操作與決策互動
UI SHALL 只提供當下合法的操作(依狀態快照過濾);引擎要求決策(ChoiceRequired)時 MUST 以對話框呈現選項(目標選擇/保護與否/受傷順序/付費重擲),並標明是哪位玩家決策。hotseat 下 SHALL 明確標示當前輪到哪位玩家行動。

#### Scenario: 非法操作不可點
- **WHEN** MP 不足以支付某術的費用
- **THEN** 該術的攻擊宣告按鈕呈禁用狀態並顯示原因

#### Scenario: 保護對話框
- **WHEN** 引擎發出保護決策要求
- **THEN** 畫面彈出對話框列出可保護的魔物與「不保護」選項,標明由受傷方玩家選擇

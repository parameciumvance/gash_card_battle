## MODIFIED Requirements

### Requirement: 中途決策(pending choice)
效果解決需要玩家決策時(選目標、保護與否、受傷順序、可選費用),引擎 SHALL 進入等待狀態並發出 ChoiceRequired 事件,僅接受被詢問玩家的對應決策指令;其他指令 MUST 被拒絕。目標為卡片的選項 SHALL 標示卡片所在位置:區域(`zone`:場上魔物槽 `slot`、魔本 `book`、棄牌區 `discard`)、所屬玩家(`player`)與定位欄位(魔物槽 uid `slot`、頁碼 `page`、棄牌區索引 `index`);位置欄位不改變選項的值(`value`)與決策的驗證。

#### Scenario: 等待決策時拒絕其他指令
- **WHEN** 引擎等待防方保護決策,攻方提交 pass
- **THEN** 攻方指令被拒絕,狀態仍在等待防方決策

#### Scenario: 選項標示位置
- **WHEN** 效果要求從自己魔本第 9 頁與第 21 頁的同名搭檔中選一張
- **THEN** 兩個選項分別帶 `zone: "book"`、自己的 `player` 與 `page` 9、21,值為頁碼

#### Scenario: 保護選項標示魔物槽
- **WHEN** 引擎發出保護決策要求
- **THEN** 每個可保護魔物的選項帶 `zone: "slot"`、受方的 `player` 與該魔物槽的 uid;「不保護」只有 `label`

## MODIFIED Requirements

### Requirement: 產品篩選分排
產品網格 SHALL 依設定檔分排列出產品,每排是一個賽季的系列:
- 第 1 排:LEVEL:1
- 第 2 排:LEVEL:2、魔本ファイル第1弾、魔本拡張シート LEVEL:1
- 第 3 排:LEVEL:3、ガッシュ・ベルと仲間達、ゼオンと最凶魔物達、LIMITED EDITION Ⅰ、スペシャルボックス、魔本ファイル第2弾、魔本拡張シート LEVEL:2
- 第 4 排:特典カード(PR)

排內只列有開放卡片的產品(見「卡池不顯示尚未開放的卡」),一排沒有任何可列的產品時整排不顯示。

一排的寬度放不下時 SHALL 換行,續行 SHALL 比該排第一格縮排,表示仍屬同一系列。

再收錄產品(THE BEST BOOSTER 1、THE BEST BOOSTER 2、REVISED EDITION、FILE:1、LEVEL:S)MUST NOT 列出。

產品 SHALL 以產品圖為圖示,並以目前語言顯示產品名稱;特典カード以「PR」字樣的圖示表示。

#### Scenario: 產品分排且不列再收錄產品
- **WHEN** 所有產品都有開放卡片,玩家展開產品網格
- **THEN** 第一排為 LEVEL:1
- **THEN** 第二排為 LEVEL:2、魔本ファイル第1弾、魔本拡張シート LEVEL:1
- **THEN** 第三排為 LEVEL:3、ガッシュ・ベルと仲間達、ゼオンと最凶魔物達、LIMITED EDITION Ⅰ、スペシャルボックス、魔本ファイル第2弾、魔本拡張シート LEVEL:2
- **THEN** 最後一排為特典カード
- **THEN** 沒有 THE BEST BOOSTER、REVISED EDITION、FILE:1、LEVEL:S

#### Scenario: 放不下時換行縮排
- **WHEN** 所有產品都有開放卡片,在手機寬度展開產品網格
- **THEN** 第三排分成多行
- **THEN** 續行的第一格比 LEVEL:3 靠右
- **THEN** 頁面沒有水平捲動

#### Scenario: 產品名稱依語言
- **WHEN** 語言為英文,玩家展開產品網格
- **THEN** 各產品以英文名稱標示

#### Scenario: 新產品在卡片開放前不列出
- **WHEN** 第 3 賽季的新卡都還在尚未開放清單中,玩家展開產品網格
- **THEN** 產品網格與本 change 之前相同:LEVEL:1 / LEVEL:2、魔本ファイル第1弾 / LEVEL:3、ガッシュ・ベルと仲間達、ゼオンと最凶魔物達
- **THEN** 沒有 LIMITED EDITION Ⅰ、スペシャルボックス、魔本ファイル第2弾、魔本拡張シート與特典カード

#### Scenario: 選特典卡
- **WHEN** 某張 PR 卡已開放,玩家在產品網格選擇特典カード
- **THEN** 卡池只顯示收錄產品含 PR 的已開放卡

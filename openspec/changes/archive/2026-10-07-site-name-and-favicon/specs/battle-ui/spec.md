## ADDED Requirements

### Requirement: 網站名稱與圖示
網站名稱 SHALL 為「Gash Card Battle Online」,各語言相同、不翻譯;瀏覽器分頁標題 SHALL 為此名稱。首頁與頂欄 SHALL 以標題字呈現:五圓紋徽章(與網頁圖示相同)加上 GASH / CARD BATTLE / ONLINE 三行,ONLINE 置中;頂欄排成一行;輔助技術 SHALL 讀到完整名稱。網頁 SHALL 提供網頁圖示:魔本紅底的圓角方塊上畫金色的魔本五圓紋,在瀏覽器分頁的小尺寸下仍可辨識。

#### Scenario: 各語言名稱相同
- **WHEN** 玩家以日文或英文開啟首頁
- **THEN** 分頁標題為「Gash Card Battle Online」;首頁標題字為徽章與 GASH / CARD BATTLE / ONLINE,ONLINE 置中,螢幕閱讀器讀到「Gash Card Battle Online」

#### Scenario: 分頁顯示五圓紋圖示
- **WHEN** 玩家在瀏覽器開啟網站
- **THEN** 分頁顯示紅底金色五圓紋的圖示

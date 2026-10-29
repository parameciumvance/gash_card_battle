# 產品圖

卡池產品篩選網格的圖示。檔名為產品代號加 `.webp`,缺圖時網格只顯示產品名稱。

| 代號 | 產品 |
|---|---|
| `level-1` | LEVEL:1 |
| `level-2` | LEVEL:2 |
| `mahon-file` | 魔本ファイル第1弾(別売魔本) |
| `level-3` | LEVEL:3 |
| `cardset-gash-nakama` | カードセット ガッシュ・ベルと仲間達 |
| `cardset-zeon` | カードセット ゼオンと最凶魔物達 |
| `limited-1` | LIMITED EDITION Ⅰ |
| `special-box` | スペシャルボックス |
| `mahon-file-2` | 魔本ファイル第2弾 |
| `ex-sheet-1` | 魔本拡張シート LEVEL:1 |
| `ex-sheet-2` | 魔本拡張シート LEVEL:2 |
| `promo` | 特典カード(PR) |

目前的圖取自維護者的產品照片(補充包 / 卡組盒、魔本ファイル第1、2弾、LIMITED EDITION Ⅰ、スペシャルボックス、魔本拡張シート),長邊縮到 400px 轉 WebP。
特典卡不是單一商品,`promo.webp` 是以介面配色(深藍底、金框、金色「PR」字)產生的圖示。
網格中每格約 96×96 CSS px 顯示(圖片以 `object-fit: contain` 縮放,不裁切),換圖時建議長邊 192px 以上。
要顯示哪些產品、如何分排,見 `frontend/pool-filters.json`。

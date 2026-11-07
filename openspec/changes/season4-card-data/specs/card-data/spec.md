# Spec Delta

## MODIFIED Requirements

### Requirement: 賽季定義
`data/seasons.json` SHALL 定義各賽季每種卡號前綴的最大編號,以及特別歸屬某賽季的卡號。目前的定義:
- 第 1 賽季:M-015、S-028、P-009、E-015、PR-002
- 第 2 賽季:M-034、S-058、P-019、E-027、PR-004、Ex-024
- 第 3 賽季:M-069、S-112、P-043、E-049、PR-010、Ex-048
- 第 4 賽季:M-085、S-146、P-050、E-054、PR-013、Ex-074、MJ-006
- 特別歸屬:Ex-100、Ex-101 屬第 3 賽季;Ex-000、Ex-099 屬第 4 賽季

一張卡的賽季 SHALL 為特別歸屬的賽季;沒有特別歸屬時,為該前綴最大編號不小於其編號的最早賽季。沒有任何賽季包含的卡沒有賽季。

#### Scenario: 卡片的賽季
- **WHEN** 查詢 M-015、M-016、S-106、M-053 的賽季
- **THEN** 依序為第 1、2、3、3 賽季

#### Scenario: 前綴在早期賽季沒有定義
- **WHEN** 查詢 Ex-010 的賽季
- **THEN** 為第 2 賽季(第 1 賽季沒有 Ex 前綴)

#### Scenario: 特別歸屬
- **WHEN** 查詢 Ex-000 的賽季
- **THEN** 為第 4 賽季,雖然它的編號在第 2 賽季的 Ex 範圍內

#### Scenario: 特別歸屬到較早的賽季
- **WHEN** 查詢 Ex-100、Ex-101、Ex-099 的賽季
- **THEN** 依序為第 3、3、4 賽季,雖然它們的編號不在任何賽季的 Ex 範圍內

#### Scenario: PR 卡的賽季
- **WHEN** 查詢 PR-004、PR-005、PR-010、PR-011、PR-013 的賽季
- **THEN** 依序為第 2、3、3、4、4 賽季

#### Scenario: 第 4 賽季的卡
- **WHEN** 查詢 M-085、S-146、Ex-074、MJ-006、M-086、MJ-007 的賽季
- **THEN** M-085、S-146、Ex-074、MJ-006 為第 4 賽季;M-086、MJ-007 沒有賽季

### Requirement: 第 3 賽季卡片資料
卡片資料 SHALL 涵蓋第三彈以後、隨第 3 賽季收錄的 95 張卡:
- M-054–M-069
- S-107–S-112
- P-036–P-043
- E-044–E-049
- PR-001–PR-011
- Ex-001–Ex-048

每張卡 SHALL 有日文權威資料(`cards_ja.csv`)、`cards.json` 的資料,以及四種語言的卡片文字。繁中卡名、繁中效果文與英文效果文是初版翻譯,尚待校對。這些卡各自的賽季依「賽季定義」(例如 PR-011 屬第 4 賽季)。

擴張卡的卡號 SHALL 依 atwiki 寫作 `Ex-`(例如 `Ex-001`)。這 95 張 SHALL 全部列入尚未開放的卡,直到各自的效果實作完成。

#### Scenario: 第 3 賽季卡號齊全
- **WHEN** 載入卡片資料
- **THEN** 含 M-054–M-069、S-107–S-112、P-036–P-043、E-044–E-049、PR-001–PR-011、Ex-001–Ex-048 的每一張
- **THEN** 四種語言的卡片文字都有對應項目

#### Scenario: 新卡尚未開放
- **WHEN** 建房時的自訂牌組含 Ex-001
- **THEN** 回應 422 與原因碼 `deck.card_pending`

#### Scenario: 擴張卡號的寫法
- **WHEN** 查詢卡號 `Ex-025`
- **THEN** 找到 Ex-025(ガッシュ・ベル,魔物)
- **THEN** 卡片資料中沒有 `EX-` 開頭的卡號

### Requirement: atwiki 抓取的頁面與範圍
`tools/scrape_ja_effects.py` SHALL 從 atwiki 的產品頁(如 LEVEL:1/2 booster 頁)的「収録カード」區塊,依 魔物/戰術/パートナー/イベント/MJ12 分類取得每張卡的卡號、名稱與個別卡頁連結;逐一抓個別卡頁,解析 `<blockquote>` 內的官方資料區塊。產品頁之外也 SHALL 接受同格式的商品頁(如カードセット、魔本ファイル)。可指定卡號範圍(例如 `M-032:M-053`),只抓範圍內的卡;商品頁收錄範圍外的卡(例如魔本ファイル的後續彈卡片)MUST 略過。輸出至 `data/cards_ja.csv`;已存在於輸出檔的卡號 MUST 跳過(支援分批執行、中斷續抓),每處理完一張卡 MUST 立即寫回檔案。

#### Scenario: 依卡號範圍篩選
- **WHEN** 以範圍 `M-032:M-034` 抓魔本ファイル的商品頁
- **THEN** 只抓 M-032 至 M-034,頁面上的其他卡(如 M-059)不抓

#### Scenario: MJ12 分類
- **WHEN** 抓 LEVEL:4 的產品頁
- **THEN** 「MJ12」分類下的 MJ-001 至 MJ-006 也被取得,類型為 MJ12

### Requirement: atwiki 資料頭的 token 分類
第一段(捨棄第一行卡號+名稱後)的資料頭 SHALL 逐 token(全形空白分隔)封閉分類,每個 token MUST 落在下列其中一類,否則視為未知標籤 MUST raise(不得歸類為屬性等開放欄位,不得靜默略過):類型(魔物/戰術/パートナー/イベント/ＭＪ１２,已知略過;石版魔物見「石版魔物的標記」)/級別(中級→intermediate、上級→superior)/費用(「MP」前綴+數字)/傷害(「ダメージ」前綴+數字;「ダメージ?」表示傷害依效果決定,存為「?」)/power(見「atwiki 資料頭的 power 格式」)/元素屬性(水/火/雷/氷/木/風/重力/土)/效果 icon(バトル/非バトル/ジャマー)/回合欄位(「バトル攻撃」/「バトル防御」/「自分のターン」/「相手のターン」,四者換算為 A/D/AD)。

#### Scenario: 土元素
- **WHEN** 解析資料頭為「術　MP2　＋4000　ダメージ1　土」的戰術卡(如 S-065)
- **THEN** 元素為「土」,不視為未知標籤

#### Scenario: 傷害依效果決定
- **WHEN** 解析資料頭含「ダメージ?」的戰術卡(如 S-061)
- **THEN** 傷害存為「?」,不視為未知標籤

#### Scenario: MJ12 的資料頭
- **WHEN** 解析資料頭只有全形「ＭＪ１２」的卡(如 MJ-004)
- **THEN** 不視為未知標籤;沒有必填欄位,下一行起為效果文

### Requirement: atwiki 魔物卡與事件卡的身分
- 魔物卡:MUST NOT 自動解析 related_mamodo_ja(不論基本形態或變身形態,一律留空;基本形態亦不自我參照為自己的 name_ja)——此身分之後如需使用,由人工從效果內文判斷。魔物卡 SHALL 解析對應搭檔的身分尾行:段落符合「パートナー＝<名字>」格式(純文字,無連結),取名字存入 related_partner_ja 並排除於效果文之外——與搭檔卡的「魔物＝X」尾行鏡像對稱(搭檔宣告對應魔物,魔物宣告對應搭檔)。魔物卡 MUST 有 related_partner_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,若卡號登記於已知沒有搭檔的魔物(卡片本身沒有搭檔,如 PR-012 黒騎士)則 related_partner_ja 為空,否則 MUST raise,檢查時機與 related_mamodo_ja 相同(尾行解析完成後)。
- 事件卡:MUST NOT 有 related_mamodo_ja 或 related_partner_ja(對照英文資料確認事件卡無此概念)。

#### Scenario: 魔物卡一律不解析對應魔物
- **WHEN** 解析任一張魔物卡(不論基本或變身形態)
- **THEN** related_mamodo_ja 恆為空字串,不嘗試從卡名或效果文推論

#### Scenario: 魔物卡解析對應搭檔
- **WHEN** 解析一張魔物卡,資料區塊最後一行為「パートナー＝高嶺清麿」
- **THEN** related_partner_ja 為「高嶺清麿」,該行不出現在 effect_ja 中

#### Scenario: 魔物卡缺少對應搭檔且未登記已知缺漏時報錯
- **WHEN** 一張魔物卡讀完效果文仍解析不出 related_partner_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

#### Scenario: 已知沒有搭檔的魔物
- **WHEN** 解析 PR-012 黒騎士(卡頁沒有「パートナー＝」行)
- **THEN** 不報錯,related_partner_ja 為空,效果文不含風味文與收錄產品

## ADDED Requirements

### Requirement: 第 4 賽季卡片資料
卡片資料 SHALL 涵蓋第 4 賽季的 98 張卡,以及第 3 賽季補收的 2 張:
- LEVEL:4:M-070–M-085、S-113–S-146、P-044–P-050、E-050–E-054、MJ-001–MJ-006
- 魔本拡張シート LEVEL:3:Ex-051–Ex-074
- 電撃フェスタ2004春の陣 プロモーションシート:Ex-000、Ex-049、Ex-050、Ex-099
- 特典卡:PR-012、PR-013
- 第 3 賽季補收(DX赤い魔本 スペシャルカードエディション附錄):Ex-100、Ex-101

每張卡 SHALL 有日文權威資料、`cards.json` 的資料與四種語言的卡片文字。繁中卡名、繁中效果文與英文效果文是初版翻譯,尚待校對。這 100 張 SHALL 全部列入尚未開放的卡,直到各自的效果實作完成。卡片資料 SHALL 共 432 張。

#### Scenario: 卡號齊全
- **WHEN** 載入卡片資料
- **THEN** 含上述每一張卡,四種語言的卡片文字都有對應項目
- **THEN** `cards.json` 共 432 張

#### Scenario: 新卡尚未開放
- **WHEN** 建房時的自訂牌組含 M-070、Ex-100 或 MJ-001
- **THEN** 回應 422 與原因碼 `deck.card_pending`

### Requirement: 第 4 賽季產品的代號
「收錄產品資料」的對照表 SHALL 在 `ex-sheet-2` 之後、`promo` 之前依序包含:DX赤い魔本 → `dx-red-book`、LEVEL:4 → `level-4`、拡張3 → `ex-sheet-3`、電撃フェスタ2004春の陣 → `festa-2004-spring`。

atwiki 卡頁把 DX赤い魔本 與 電撃フェスタ2004春の陣 的附錄卡都寫作「限定拡張」。轉換 SHALL 依卡號區分:Ex-100、Ex-101 轉為 `dx-red-book`;Ex-000、Ex-049、Ex-050、Ex-099 轉為 `festa-2004-spring`;其他卡號的「限定拡張」MUST 報錯,不可猜測。

#### Scenario: 限定拡張分兩個產品
- **WHEN** 轉換 `sets_ja` 為「限定拡張|TBB2」的 Ex-100 與 Ex-049
- **THEN** Ex-100 的 `sets` 為 `["dx-red-book", "tbb2"]`,Ex-049 的 `sets` 為 `["festa-2004-spring", "tbb2"]`

#### Scenario: 未登記的限定拡張
- **WHEN** 轉換一張不在上述卡號中、`sets_ja` 含「限定拡張」的卡
- **THEN** 報錯並指出卡號

#### Scenario: LEVEL:4 與拡張シート LEVEL:3
- **WHEN** 轉換 M-070(`LEVEL:4|TBB1|RE`)與 Ex-051(`拡張3|TBB1`)
- **THEN** 兩者的 `sets` 依序為 `["level-4", "tbb1", "re"]` 與 `["ex-sheet-3", "tbb1"]`

### Requirement: 石版魔物的標記
atwiki 卡頁資料頭以「石版魔物」取代「魔物」的卡(如 Ex-056「石版魔物　4500」)SHALL 解析為魔物卡,並在 `cards.json` 記 `stone_tablet: true`;其他卡 MUST NOT 有這個欄位。石版魔物在規則上與一般魔物相同,只有指定石版魔物的效果會區分(atwiki 規則頁「石版魔物」)。

#### Scenario: 石版魔物
- **WHEN** 轉換 Ex-056、Ex-057、Ex-058
- **THEN** 類型為魔物,`stone_tablet` 為 true,魔力等其他欄位照一般魔物解析

#### Scenario: 一般魔物
- **WHEN** 轉換 Ex-051
- **THEN** 沒有 `stone_tablet` 欄位

### Requirement: 多個效果圖示
資料頭有多個效果圖示的卡(各效果有自己的圖示,如 M-080「ジャマー」「バトル」)SHALL 在 `cards.json` 依資料頭順序記錄全部圖示於 `effect_icons`,且 `effect_icon` 為 null;MUST NOT 只保留其中一個。只有一個圖示的卡照舊只有 `effect_icon`。

#### Scenario: 兩個效果圖示
- **WHEN** 轉換 M-080
- **THEN** `effect_icons` 為 `["jammer", "battle"]`,`effect_icon` 為 null

### Requirement: 魔力倍率的寫法
戰術的魔力倍率(數字加倍率後綴)SHALL 接受乘號「×」與英文字母「x」兩種寫法,視為相同(Ex-050 的來源寫作「1000x」)。

#### Scenario: 字母 x
- **WHEN** 轉換 power 為「1000x」的 Ex-050
- **THEN** `power` 為 `{"special": true, "per_heads": 1000}`

### Requirement: MJ12 卡
MJ12(マジョスティック12,LEVEL:4 起)SHALL 是第 6 種卡片類型,`cards.json` 的 `type` 為 `mj12`,卡號前綴為 `MJ-`。MJ12 卡沒有魔力、費用、級別等資料頭欄位(`power` 為空物件、`cost` 為 null);效果的使用代價(如「MPを1へらす→」)寫在效果文中。

規則上 MJ12 是放到場上的卡(atwiki 規則頁「MJ12」):不裝在魔物上、張數不限、同名只能有 1 張,場上的 MJ12 的效果可在雙方的戰鬥階段使用。對戰中的處理留到實作 MJ12 效果的批次,並在那時寫進 `game-engine` 規格。

#### Scenario: MJ12 卡的資料
- **WHEN** 載入 MJ-001 至 MJ-006
- **THEN** 類型都是 `mj12`,`cost` 為 null

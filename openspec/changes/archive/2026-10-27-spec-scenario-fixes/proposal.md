# Proposal

## Why

- `game-engine` 的「戰鬥階段輪流行動權(かわりばんこ)」沒寫一場戰鬥結束、回到非戰鬥中時由誰先行動;這條規則(回合玩家先行動,atwiki 規則頁「かわりばんこのルール」,使用者已確認)目前只存在於引擎實作與 `tests/test_engine.py` 的一行斷言。
- `card-data` 在 `card-image-source` 歸檔時,因 MODIFIED 不能刪除既有情境,保留了「image_url 直接從 xlsx 抽取」「S-042 改直接讀取後找回卡圖連結」兩個名稱,內容卻是「沒有 `image_url`」,名稱與內容矛盾。

## What Changes

- `game-engine`:「戰鬥階段輪流行動權」補上戰鬥結束後行動權回到回合玩家,並加情境。只補規格,實作與行為不變。
- `card-data`:「卡片資料轉換」的情境整理:「image_url 直接從 xlsx 抽取」改名為「cards.json 不含卡圖連結」;刪除「S-042 改直接讀取後找回卡圖連結」(S-042 的卡圖連結問題已隨 `image_url` 移除而不存在,沒有對應的行為)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:「戰鬥階段輪流行動權(かわりばんこ)」加戰鬥結束後的行動權。
- `card-data`:「卡片資料轉換」情境改名與刪除(需求本文不變)。

## Impact

- 只有規格文件:`openspec/specs/game-engine/spec.md`、`openspec/specs/card-data/spec.md`,以及 `game-engine/design.md` 的規則出處。程式與測試不變。

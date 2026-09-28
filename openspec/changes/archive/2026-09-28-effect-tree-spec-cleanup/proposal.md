## Why

`effect-tree` spec 混入了實作細節:內部資料鍵名(`tree_choice`、`tree_cont`、`CHOICE_KEY`、`CONT_KEY`)、續體的欄位格式、註冊檔的縮排排版。這些不是可觀察的行為,而且已經開始與程式脫節(續體實際上還多了 `floor`,spec 仍寫 `(effect_id, path, ctx)`)。專案層級的 `openspec/design.md` 已經建立,實作細節有了該放的地方,spec 可以回到只描述行為與可測試的約束。

## What Changes

- 「pending 依專屬標記分派」:改寫為行為描述——由效果樹建立的決策交回效果樹、擲幣確認的決策交給原本的 M-012 / M-019 處理、`prompt` 不可與引擎保留的決策種類重複;不再寫出內部鍵名。
- 「停點續體為純資料」:移除規定 `PendingChoice.data["tree_choice"]` 欄位格式的情境;保留「不存閉包、只存可 JSON 序列化的資料」「從停點之後繼續」「JSON 往返後仍可恢復」。
- 「付費重擲節點在節點內部迴圈」:移除 `CONT_KEY` / `CHOICE_KEY` 的鍵名敘述,其餘行為不變。
- 「註冊檔逐卡集中登記」:移除縮排、收尾括號對齊等排版慣例與對應情境(排版規則已寫在 `tree_cards.py` 開頭);保留依卡號排序、每卡集中、邏輯不寫在註冊檔。
- 「Standby.then 限定同步完成」維持不變。
- 移出的鍵名與續體格式記錄在 `openspec/design.md` 第 2.2 節(已有,必要時補充)。

純文件變更,不改程式與測試。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `effect-tree`:改寫「pending 依專屬標記分派」「停點續體為純資料」「付費重擲節點在節點內部迴圈」「註冊檔逐卡集中登記」四項需求的敘述,移除實作細節,可觀察行為與約束不變。

## Impact

- `openspec/specs/effect-tree/spec.md`(歸檔時同步)
- `openspec/design.md`(確認第 2.2 節涵蓋移出的內容)
- 程式、測試、API、前端皆不受影響。

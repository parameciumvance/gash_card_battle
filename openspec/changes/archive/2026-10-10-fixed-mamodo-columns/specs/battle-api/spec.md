## ADDED Requirements

### Requirement: 魔物槽欄位快照
狀態快照中每個魔物槽 SHALL 含其欄位(0–2),所有視角相同(場上位置是公開資訊)。

#### Scenario: 快照帶欄位
- **WHEN** 第 0 欄的魔物送墓後查詢狀態
- **THEN** 其餘魔物槽的欄位分別為 1 與 2,沒有欄位為 0 的魔物槽

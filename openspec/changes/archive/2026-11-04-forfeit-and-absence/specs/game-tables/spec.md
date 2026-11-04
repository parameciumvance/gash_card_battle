## MODIFIED Requirements

### Requirement: 牌桌房間的回收
牌桌對應的房間因閒置被回收,或因雙方都沒有回應而關閉(見 `online-room`)時,系統 SHALL 一併空出該牌桌。

#### Scenario: 閒置回收
- **WHEN** 牌桌對應的房間閒置超過回收時間被刪除
- **THEN** 該牌桌轉為空

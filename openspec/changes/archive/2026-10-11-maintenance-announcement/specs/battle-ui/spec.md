## ADDED Requirements

### Requirement: 維護公告橫幅
有公告時,UI SHALL 在頂欄下方顯示公告橫幅,首頁、設定頁與對局畫面都 SHALL 顯示。訊息 SHALL 依目前語言選擇,該語言沒有時依序改用 `zh-TW`、任一語言;文字 MUST 以純文字呈現。UI SHALL 在載入時與之後每 2 分鐘查詢公告,讓已在對局中的玩家也能看到新公告;公告撤下或過期後 SHALL 移除橫幅。橫幅 SHALL 可關閉;同一則公告(依 `id`)關閉後 MUST NOT 再顯示,新的公告(不同 `id`)SHALL 再顯示。

#### Scenario: 對局中收到維護公告
- **WHEN** 玩家正在對局,伺服器發布新公告
- **THEN** 2 分鐘內頂欄下方出現公告橫幅,對局照常進行

#### Scenario: 關閉後不再顯示
- **WHEN** 玩家關閉某則公告後重新整理
- **THEN** 該則公告不再顯示;之後發布不同 `id` 的公告時再顯示

#### Scenario: 依語言顯示
- **WHEN** 語言為英文,公告有 `en` 與 `zh-TW` 的訊息
- **THEN** 橫幅顯示 `en` 的訊息

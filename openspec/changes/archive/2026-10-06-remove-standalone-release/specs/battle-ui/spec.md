## MODIFIED Requirements

### Requirement: 公開邀請連結
建房後顯示的加入 / 觀戰連結 SHALL 以 `location.origin` 為基底組成,並提供一鍵複製。

#### Scenario: 以目前網址組連結
- **WHEN** 玩家 A 在 `https://card-battle.example` 建立房間,房號為 `ABC123`
- **THEN** 等待畫面的加入連結為 `https://card-battle.example/?join=ABC123`,觀戰連結也以 `https://card-battle.example` 為基底

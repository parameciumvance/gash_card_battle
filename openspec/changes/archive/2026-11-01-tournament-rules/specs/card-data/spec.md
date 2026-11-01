## ADDED Requirements

### Requirement: PR 卡同編號限 1 張
構築規則驗證 SHALL 拒絕同一個 `PR-` 開頭卡號放入 2 張以上的魔書,原因碼 `deck.pr_copies`(大會規則「プロモーションカードは1種類につき1枚まで入れられる」,atwiki「ルール」pages/87;不設開關,所有構築驗證一律適用,含建房、加入、牌桌入座、預組與 NPC 牌組)。其他卡號(含 `Ex-` 開頭的擴張卡)仍依同號 ≤4。

#### Scenario: 同一張 PR 卡 2 張被拒絕
- **WHEN** 驗證放了 2 張 PR-001、其他都合法的魔書
- **THEN** 驗證失敗,原因碼 `deck.pr_copies`

#### Scenario: 不同 PR 卡各 1 張可以
- **WHEN** 驗證放了 PR-001、PR-006 各 1 張的合法魔書
- **THEN** 驗證通過

#### Scenario: Ex 卡不受限
- **WHEN** 驗證放了 4 張同一 Ex 卡的合法魔書
- **THEN** 驗證通過

# Tasks

## 1. 規格

- [x] 1.1 確認既有測試涵蓋新情境:`tests/test_engine.py` 有斷言戰鬥結束後行動權在回合玩家,`python -m pytest tests/test_engine.py -q` 通過
- [x] 1.2 `openspec/specs/card-data/spec.md`:「image_url 直接從 xlsx 抽取」改名為「cards.json 不含卡圖連結」(WHEN 轉換執行完成,THEN 每張卡都沒有 `image_url`,xlsx 的卡圖超連結不讀取),刪除「S-042 改直接讀取後找回卡圖連結」;`openspec validate card-data --type spec` 通過

## 2. 收尾

- [x] 2.1 Reconciliation:`game-engine/design.md` 記戰鬥結束後行動權的規則出處(atwiki「かわりばんこのルール」,使用者確認);`openspec validate --all` 通過

## Workflow follow-up

- 使用者指示後歸檔並提交(歸檔時同步 game-engine 的 delta spec)。

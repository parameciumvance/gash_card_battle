# local-test-mode — 設計

端點在 `src/gash/api/app.py`(`get_debug_state` / `post_debug_state`),權限檢查集中在 `_check_cheat_access`。前端面板見 `battle-ui`「金手指面板」。

## 行為決定與理由

### 金手指也開放給 NPC 房

**相關規格:** `local-test-mode` › 需求「金手指端點僅限本機房與 NPC 房」

**決定:** NPC 房的玩家可讀寫雙方(含 NPC)的 book 與 MP。

**理由:** NPC 房(特別是木人樁)常用來擺盤面測試效果;看到 NPC 的魔本是玩家自己選擇使用的測試工具。NPC 仍只透過自己的視角得知盤面(見 `npc-opponent`)。

**依據:** 專案負責人於規劃 NPC 對戰時選定。

**確認狀態:** `Project Decision`

### 觀戰者不能使用金手指

**相關規格:** `local-test-mode` › 需求「金手指端點僅限本機房與 NPC 房」 › 情境「觀戰者請求被拒」

**決定:** 本機房與 NPC 房的觀戰 token 讀取或套用金手指都回 403。

**理由:** 原本 GET 沒有擋觀戰者,觀戰者可讀到雙方完整魔本,與 `online-room`「觀戰」只給公開資訊的要求矛盾。

**依據:** 在 NPC 對戰的規劃中發現,經專案負責人確認採用(改變了本機房原本未文件化的行為)。

**確認狀態:** `Project Decision`

## 1. 資料管線

- [x] 1.1 extract_cards.py 擴充過濾(Level 2 + "Series 1 Level 2" 例外、跨產品 sets 聯集、e/j 取 j 斷言),重跑產出 134 張 cards.json;下載新卡卡圖
- [x] 1.2 cards.zh-TW.json 新增 67 張中譯(卡名/屬性/效果文,詞彙表統一)

## 2. 引擎機制擴充

- [x] 2.1 被動觸發器:registry TRIGGERS(事件型,深度上限 4)與 QUERY_HOOKS(查詢型),engine emit 後派發;機制單元測試
- [x] 2.2 無術攻擊:declare_attack mode="mamodo"、BattleState 固定合計魔力、battle_started 事件與 views/log 讀點盤查;完整戰鬥測試
- [x] 2.3 書內/墓地搜卡原語:search_book、search_opponent_book(book_revealed+棄置+MP 懲罰)、return_to_book、discarded_this_turn 追蹤;每回合一次翻頁效果旗標
- [x] 2.4 疊放擴充:detach_top(下層保留+分離觸發器)、書內取卡疊放、max_copies 查表取代同名唯一硬編
- [x] 2.5 Rider/旗標:damage_cap、injure_instead、no_attack_spell、mamodo_locked、no_mamodo_effects、no_sacrifice_no_protect;各檢查點接線與測試

## 3. 卡片 handler(67 張,每張至少一測)

- [x] 3.1 香草術與資料驅動卡(S-029/030/044/047/049-055 等)共用模板測試
- [x] 3.2 賈修/布拉哥/海德家族(M-016~018、M-021、S-031~038、P-010~012)
- [x] 3.3 佐菲斯/波克利歐/羅布諾斯家族(M-022~025、S-039~043、P-013~015、E-016~017)
- [x] 3.4 馬爾斯/巴爾特羅/尤波波/奇克洛普家族(M-026~031、S-045~058、P-016~019)
- [x] 3.5 事件卡(E-018~027,含 e/j 差異 4 張的 j 版行為測試)

## 4. 前端

- [x] 4.1 選書對話框(對頁網格、book_page 選項渲染、對手書檢視同款)
- [x] 4.2 對決舞台與 log 支援無術攻擊顯示(魔物名代替術名)

## 5. 驗證

- [x] 5.1 全量 pytest(既有 115 + 新增)全綠;抽取斷言(134 張、e/j 取 j)
- [x] 5.2 E2E:構築含 Level 2 卡的牌組打完整場(含 M-027 無術攻擊、搜卡對話框)、雙視角無資訊洩露抽查、截圖抽查

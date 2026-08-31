## 1. 房間層(後端)

- [x] 1.1 Room 模型與存放:房號產生(6 碼英數、碰撞重試)、mode/timer 設定、token 簽發(玩家×2+觀戰)、閒置回收策略
- [x] 1.2 端點:POST /api/rooms(建房;local 立即開局並回雙 token)、POST /api/rooms/{code}/join(到齊開局)、404/滿房錯誤
- [x] 1.3 token 鑑別:X-Player-Token 解析為 player index,指令 payload 的 player 欄位改由伺服器填入;觀戰 token 提交指令回 403
- [x] 1.4 移除舊 /api/games 直建端點,既有 API 測試遷移至房間流程

## 2. 視角過濾(後端)

- [x] 2.1 snapshot(game, viewer):對手/觀戰視角 open_pages 只留頁碼;pending 對非決策者去除 options/item;本機模式全視角
- [x] 2.2 事件過濾 visible(ev, viewer):book_revealed/pages_peeked 僅推 viewer;choice_required 對非決策者裁剪;GET events?since 同樣過濾
- [x] 2.3 視角測試:同一局面產出 viewer=0/1/spectator 三份快照與事件流,斷言無洩露(含 M-011 檢視、E-014 偷看、E-012 選頁)

## 3. WebSocket 推送

- [x] 3.1 WS /api/rooms/{code}/ws?token=...:連線鑑別、welcome(視角快照+next_seq)、連線集合管理與斷線清理
- [x] 3.2 指令提交後向房內全部連線廣播各自過濾的事件批次;POST 回應與 WS 推送以 seq 冪等
- [x] 3.3 整合測試:建房→join→開局廣播→出招→雙端收到各自版本→重連 welcome 對齊 seq

## 4. 回合計時器

- [x] 4.1 「等待輸入者」推導函式(start/非戰鬥/battle_in/防禦步/效果步/pending 各狀態)與 deadline 管理(等待者變更即重置)
- [x] 4.2 asyncio 逾時任務:代送安全預設指令(flip 0/pass/迎戰/不防禦/不保護/保留硬幣/放棄重擲/pick 第一項),事件標記 timeout
- [x] 4.3 計時器測試:短 timer 驗證各狀態的代打與 deadline 重置;timer=關 不代打

## 5. 前端

- [x] 5.1 首頁入口:本機對戰/建立房間(計時選項、顯示房號與分享連結、等待對手畫面)/加入房間(輸入房號+join_url 直達);token 存 localStorage 供重入
- [x] 5.2 WS client:連線/welcome/事件流渲染、seq 去重、自動重連與狀態補齊、連線狀態列
- [x] 5.3 線上視角:自己在下方的翻轉渲染、對手翻開頁卡背+頁碼、只啟用自己的行動按鈕、對手決策中的等待提示;觀戰視角(雙卡背、無操作)
- [x] 5.4 計時倒數顯示與逾時代打的 log 標示;i18n 新增房間/連線/計時相關字串
- [x] 5.5 本機模式回歸:沿用現行全視角畫面走房間 local 流程,行為與 v1 一致

## 6. 收尾

- [x] 6.1 全量測試綠燈(既有引擎/卡片測試不動,API 測試已遷移)+ 雙瀏覽器實測:建房→join→對戰→斷線重連→觀戰→計時逾時
- [x] 6.2 README 更新:約戰流程、觀戰、計時說明、記憶體對局限制(重啟失局)

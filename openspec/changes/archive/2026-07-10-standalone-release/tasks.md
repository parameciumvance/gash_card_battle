# Tasks: standalone-release

## 1. 資源解析(paths.py)

- [x] 1.1 新增 `src/gash/paths.py`:`app_root()`(凍結環境走 `sys._MEIPASS`,否則 repo 佈局)與 `assets_dir()`(GASH_ASSETS_DIR → exe 旁 assets/ → 使用者資料夾 → repo frontend/assets/,含 `installed`/`install_dir` 狀態)
- [x] 1.2 `engine/cards.py` 的 `DATA_DIR` 與 `api/app.py` 的 `ROOT`/`FRONTEND_DIR` 改走 paths.py;卡圖改為獨立 mount(掛解析出的目錄,置於 `/static` 之前)
- [x] 1.3 單元測試:解析順序(env 優先、逐層 fallback、全缺時回報未安裝)、開發模式路徑與現況等價

## 2. meta API 與前端

- [x] 2.1 `GET /api/meta`:回傳 `tunnel_url` 與 `assets`(installed/count/expected/install_dir);expected 取 card_db 張數
- [x] 2.2 前端 boot 取 meta:建房等待畫面的加入/觀戰連結改以 `tunnel_url` 為基底(無通道維持 location.origin),一鍵複製
- [x] 2.3 首頁卡圖未安裝/不足的非阻斷提示(含 install_dir);`cardEl` 的 `img.art` onerror 改掛 `back.jpg` 佔位(防重試迴圈)
- [x] 2.4 API 測試(meta 內容、卡圖 mount 等價)+ i18n 新字串

## 3. Launcher

- [x] 3.1 `src/gash/launcher.py`:埠號探測、uvicorn 單 worker 綁 127.0.0.1、`webbrowser.open`、Ctrl-C 清理子行程;`python -m gash.launcher` 可執行
- [x] 3.2 cloudflared 子行程:偵測 exe 旁二進位、`tunnel --url` 啟動、解析 trycloudflare 網址(30 秒逾時)、成功後寫入 app 狀態、失敗降級並保留輸出
- [x] 3.3 launcher 測試(埠避讓、無 cloudflared 降級、網址解析函式以樣本輸出測)

## 4. 打包與驗證

- [x] 4.1 `tools/build_release.py` + PyInstaller spec:onedir、datas 含 frontend(排除 assets/cards)與 data、附 cloudflared(下載+雜湊校驗或取本機)、組 `gash-card-battle-v{version}-win64.zip`
- [x] 4.2 pyproject 加 dev 依賴 pyinstaller;README 新增發行章節(維護者打包步驟、玩家 A 安裝三步驟與卡圖放置位置、每次連結不同的說明)
- [x] 4.3 E2E:開發模式全流程回歸(既有測試綠);模擬發行佈局(空 assets 目錄)驗證卡背佔位與未安裝提示
- [x] 4.4 Windows 實機驗證(手動):打包、點兩下啟動、通道網址可從外網加入對戰

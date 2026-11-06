# Tasks

## 1. 失敗截圖

- [x] 1.1 `tests/conftest.py` 加測試失敗時截下 `browser` 所有頁面的 hook,存到 `test-results/`;`.gitignore` 排除 `test-results/`。以一個故意失敗的瀏覽器測試在本機確認會產生截圖、檔名對應測試名稱,通過的測試與非瀏覽器測試失敗時不產生(確認後移除該測試)

## 2. Workflow

- [x] 2.1 `test.yml`:觸發加上 `dev` 與 `workflow_call`;`cache: pip`、快取 `~/.cache/ms-playwright`、安裝 `chromium-headless-shell`;`concurrency`;`timeout-minutes: 25`;失敗時上傳 `test-results/`。以 YAML 解析與 actionlint(可用時)檢查。actionlint 下載被自動模式擋下(執行外部腳本),只做了 YAML 解析與結構檢查;實際語法由 3.1 的 CI 執行驗證
- [x] 2.2 `deploy.yml`:新增以 `workflow_call` 呼叫 `test.yml` 的 `test` job,`build-and-push` 設 `needs: test`;原有的更新內容檢查、建置、Release 不變。以 YAML 解析與 actionlint(可用時)檢查。actionlint 下載被自動模式擋下(執行外部腳本),只做了 YAML 解析與結構檢查;實際語法由 3.1 的 CI 執行驗證

## 3. 實際驗證與文件

- [x] 3.1 (使用者同意後)推 `ci-full-suite` 並開 PR 到 `dev`:CI 跑完全套,通過;略過數與本機相同(9 個被動搭檔);記錄 CI 時間。再推一個故意失敗的瀏覽器測試的 commit,確認 artifact 有截圖,之後移除該 commit。結果:第一次 4 項失敗(依卡圖裁切的測試,CI 沒有卡圖),改用假卡圖後 2095 passed、9 skipped(與本機相同);故意失敗的 commit 上傳了 test-results artifact,截圖為失敗當下的畫面,確認後以 reset + force-with-lease 移除;時間:平常約 10–12 分鐘,字型套件鏡像站慢時曾 21 分鐘,逾時改 30 分鐘;Chromium 快取命中。actionlint 未執行,語法由實際 CI 執行驗證;Deploy 的 workflow_call 要等下次推 tag 才實際執行
- [x] 3.2 README「發布新版本」補上 Deploy 會先跑全套測試、失敗時不發布;`docker-deployment` design 更新 CI 一節;`openspec validate ci-full-suite --strict` 通過;`python -m pytest tests -m "not slow and not browser" -q` 通過

## Workflow follow-up

- 歸檔前依指南 §13 同步 `docker-deployment` delta spec 與 design;歸檔提交後以 `--no-ff` 合併回 `dev`(或合併 PR),合併與推送等使用者指示。

## Decisions

### D1:版本號 = git tag

部署只在推送 `v*` tag 時觸發(`deploy.yml`),所以 tag 名稱就是「目前上線的是哪一版」最直接的答案。`pyproject.toml` 的 `version` 一直是 `0.1.0` 沒有更新,不採用。

### D2:取得順序(`gash.version.app_version()`)

1. 環境變數 `GASH_VERSION`(Docker 映像檔;映像檔裡沒有 `.git`)。
2. `data/version.txt`(單機版發行物;由 `tools/build_release.py` 寫入,不進版控)。
3. `git describe --tags --always --dirty`,在程式資源根目錄執行(開發環境)。
4. 以上都取不到:`dev`。

行程啟動後第一次取得就快取,不重複執行 git。

### D3:顯示位置

- 首頁免責聲明下方,小字。
- 意見回報的環境資訊加上 `ver=…`,放在 `lang` 之後;回報時就知道是哪一版。
- 對局中不另外顯示(頂欄空間有限);意見回報對話框在對局中也看得到。

### D4:單機版 zip 命名不變

`發行打包` 要求 zip 命名含 `pyproject.toml` 的版本號,這次不改;畫面顯示的版本號以 git tag 為準。兩者不一致的問題另外處理(見 tasks)。

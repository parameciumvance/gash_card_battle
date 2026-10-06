## 1. 先寫測試(確認修改前失敗)

- [x] 1.1 下載工具:轉檔函式把含透明圓角的 PNG 轉成同尺寸、保留透明的 WebP;續抓只跳過已有 `.webp` 的卡,只有 `.jpg` 的卡會重新下載並存成 `.webp`(以假的下載函式測,不連網)
- [x] 1.2 `/api/meta`:卡圖目錄只有 `.jpg` 時 `assets.count` 為 0,有 `.webp` 時計入
- [x] 1.3 卡圖網址:卡片元件、聚焦展示、規則頁請求 `/static/assets/cards/{卡號}.webp`;只有 `.jpg` 時以卡背佔位、不請求 `.jpg`
- [x] 1.4 既有測試的卡圖網址改為 `.webp`(`test_meta.py`、`test_static_cache.py`、`test_nonbattle_ui.py`、`test_cheat_editor.py`)

## 2. 實作

- [x] 2.1 `pyproject.toml` 的 `dev` 加入 `pillow`
- [x] 2.2 `tools/download_images.py`:下載後轉成 WebP q80 存成 `{卡號}.webp`,續抓看 `.webp`(design D1、D3)
- [x] 2.3 `app.py` 的 `/api/meta` 只計 `.webp`
- [x] 2.4 前端共用 `artUrl()`:`app.js` 卡片元件、規則頁與 `anim.js` 聚焦展示(design D4)
- [x] 2.5 `frontend/back.jpg` 縮成 465 寬(design D5)
- [x] 2.6 開發環境重新下載卡圖,確認 135 張 `.webp` 齊全、圓角透明

## 3. 文件

- [x] 3.1 README:「單機發行」的卡圖說明、「卡圖」(VPS)步驟與換格式的上傳順序、「資料管線」、目錄說明

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `card-data`、`battle-api`、`battle-ui` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`card-data/design.md` 補卡圖格式(WebP q80、在下載工具轉檔、只認一種格式)與理由
- [x] 4.3 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

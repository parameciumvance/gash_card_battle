# Production 映像檔:給 VPS 常駐部署用,與 .devcontainer/Dockerfile(開發容器)分開。
# 房間狀態存在單一行程記憶體,MUST 以單一 uvicorn 行程運作,不可多 worker/多 replica。
# 基底映像檔釘 digest(標籤會移動);升級由 Dependabot 開 PR(docker-deployment「CI 的權限與相依鎖定」)
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

WORKDIR /app

# 相依依 lock 檔安裝:版本與 hash 固定,hash 不符就建置失敗。lock 檔由 pyproject.toml 產生(見 README「更新相依套件」)
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY pyproject.toml ./
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY data/ ./data/

# 必須是 editable 安裝:src/gash/paths.py 用 __file__ 相對路徑往上推算 repo 根目錄
# 以定位 frontend/、data/,非 editable 安裝會把檔案複製進 site-packages 而算錯路徑。
# --no-deps:相依已由 lock 檔裝好;--no-build-isolation:用 lock 檔裡的 setuptools 建置,不另外下載
RUN pip install --no-cache-dir --no-deps --no-build-isolation -e .

# 版本號:CI 以觸發部署的 tag 名稱傳入(映像檔裡沒有 .git),/api/meta 回報、首頁顯示
ARG GASH_VERSION=dev
ENV GASH_VERSION=$GASH_VERSION

EXPOSE 8000

CMD ["uvicorn", "gash.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

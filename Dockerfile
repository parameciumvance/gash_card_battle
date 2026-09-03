# Production 映像檔:給 VPS 常駐部署用,與 .devcontainer/Dockerfile(開發容器)分開。
# 房間狀態存在單一行程記憶體,MUST 以單一 uvicorn 行程運作,不可多 worker/多 replica。
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY data/ ./data/

# 必須是 editable 安裝:src/gash/paths.py 用 __file__ 相對路徑往上推算 repo 根目錄
# 以定位 frontend/、data/,非 editable 安裝會把檔案複製進 site-packages 而算錯路徑。
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "gash.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# rag_lite 应用镜像（Flask）
# 构建: docker build -t your-registry/rag-lite:latest .
# 运行需配合 MySQL、Milvus 等，见 docs/Harness云端部署指南.md

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "main.py"]

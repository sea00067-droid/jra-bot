FROM python:3.11-slim-bookworm

WORKDIR /app

# 依存ライブラリのインストール
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコピー
COPY . .

# 実行コマンド
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}

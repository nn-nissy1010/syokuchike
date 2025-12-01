FROM python:3.10-slim

# 必要パッケージ
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# Python ライブラリインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコピー
COPY . .

# Streamlit 起動ポート
EXPOSE 8501

# コンテナ起動時に Streamlit を動かす
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]

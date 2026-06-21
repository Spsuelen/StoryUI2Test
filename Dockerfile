FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY interface/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download pt_core_news_sm

COPY interface/ ./interface/

EXPOSE 8501

ENV OPENAI_API_KEY=""

WORKDIR /app/interface

CMD ["streamlit", "run", "home.py", "--server.address=0.0.0.0", "--server.port=8501"]

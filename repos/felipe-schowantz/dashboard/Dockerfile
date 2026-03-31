FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    streamlit>=1.30.0 \
    plotly>=5.18.0 \
    psycopg2-binary>=2.9.9 \
    pandas>=2.1.0 \
    anthropic>=0.20.0 \
    openai>=1.10.0 \
    python-dotenv>=1.0.0

COPY dashboard/ /app/
COPY synthesis/ /app/synthesis/

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

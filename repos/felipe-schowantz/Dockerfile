FROM apache/airflow:2.9.2-python3.11

USER root

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

COPY data-pipeline/requirements.txt /requirements-pipeline.txt
RUN pip install --no-cache-dir -r /requirements-pipeline.txt

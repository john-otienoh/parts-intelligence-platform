# syntax=docker/dockerfile:1
FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libpq-dev     && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy project source into the image
COPY --chown=airflow:root . /opt/airflow/beforward_scraper
ENV PYTHONPATH="/opt/airflow/beforward_scraper:${PYTHONPATH}"

WORKDIR /opt/airflow
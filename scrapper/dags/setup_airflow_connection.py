#!/usr/bin/env python3
"""One-time setup: create Airflow connections for the BE FORWARD pipeline.

Run inside the Airflow container:
    docker compose run --rm airflow-worker python /opt/airflow/beforward_scraper/scripts/setup_airflow_connections.py

Or via the Airflow CLI:
    airflow connections add 'postgres_default' ...
"""
import os
from airflow.models import Connection
from airflow.utils.db import provide_session
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present


@provide_session
def create_connections(session=None):
    db_url = os.getenv("DATABASE_URL")
    # Parse simple postgresql://user:pass@host:port/db
    from urllib.parse import urlparse
    parsed = urlparse(db_url)

    conn_id = "postgres_default"
    conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    if conn:
        print(f"Connection '{conn_id}' already exists — skipping.")
        return

    new_conn = Connection(
        conn_id=conn_id,
        conn_type="postgres",
        host=parsed.hostname or "postgres",
        port=parsed.port or 5432,
        login=parsed.username or "postgres",
        password=parsed.password or "postgres",
        schema=parsed.path.lstrip("/") or "beforward",
    )
    session.add(new_conn)
    session.commit()
    print(f"Connection '{conn_id}' created successfully.")


if __name__ == "__main__":
    create_connections()
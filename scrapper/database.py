"""PostgreSQL connection management with SQLAlchemy 2.x and context-manager sessions."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Set
from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# from config import Config


class PostgresStore:
    """PostgreSQL connection management with SQLAlchemy 2.x and context-manager sessions."""

    def __init__(self, cfg: Config):
        self._engine = create_engine(
            cfg.db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            future=True,
        )
        self._session_factory = sessionmaker(bind=self._engine, future=True)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a transactional session that auto-commits or rolls back."""
        sess: Session = self._session_factory()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    def known_ref_nos(self) -> Set[str]:
        """Return every ref_no already present in bronze for incremental filtering."""
        with self.session() as sess:
            rows = sess.execute(
                text("SELECT DISTINCT ref_no FROM bronze.listings_raw")
            ).fetchall()
            return {r[0] for r in rows if r[0]}

    def execute_query(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute a raw SQL query and return the results as a list of dictionaries."""
        with self.session() as sess:
            result = sess.execute(text(query), params or {})
            return [dict(row) for row in result.fetchall()]

    def get_tables(self) -> Set[str]:
        """Return a set of table names in the database."""
        with self.session() as sess:
            result = sess.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )
            )
            return {row[0] for row in result.fetchall()}

    def scalar(self, stmt: str, params: dict | None = None):
        """Execute raw SQL and return a single scalar."""
        with self.session() as sess:
            return sess.execute(text(stmt), params or {}).scalar()

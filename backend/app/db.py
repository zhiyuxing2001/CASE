"""Engine and session management.

Two SQLite specifics are handled here:

* ``PRAGMA foreign_keys=ON`` — SQLite does not enforce foreign keys by
  default, so the references declared in the models would be decorative.
* ``PRAGMA journal_mode=WAL`` — lets a reader run while a write is in
  flight, which matters once the OCR review screen and the case list are
  open at the same time.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .audit import enable_audit
from .config import settings


def make_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """Create an engine with the SQLite pragmas this project relies on."""
    resolved = url or settings.resolved_database_url()
    if resolved.startswith("sqlite:///") and ":memory:" not in resolved:
        db_file = Path(resolved.removeprefix("sqlite:///"))
        db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(resolved, echo=echo, future=True)
    _install_sqlite_pragmas(engine)
    return engine


def _install_sqlite_pragmas(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            # WAL is not supported for in-memory databases.
            if ":memory:" not in str(engine.url):
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

# Every write through the application's session factory is audited. Tests
# and bulk imports build their own session maker so they can opt out.
enable_audit(SessionLocal)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

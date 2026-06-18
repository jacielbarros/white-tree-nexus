"""Engine SQLAlchemy, `SessionLocal` e `get_db()` centralizado.

Ponto único importado por routers, helpers e serviços. NÃO criar `get_db()` local.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from wtnapp import settings

_url = settings.DATABASE_URL

if _url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False, "timeout": 30}
    if ":memory:" in _url:
        # in-memory compartilhado entre conexões (testes)
        engine = create_engine(_url, connect_args=_connect_args, poolclass=StaticPool)
    else:
        engine = create_engine(_url, connect_args=_connect_args)
else:
    engine = create_engine(_url, pool_pre_ping=True)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - infra
    """Liga FKs e busy_timeout no SQLite (paridade com PostgreSQL nos testes)."""
    if engine.dialect.name == "sqlite":
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
SQLAlchemy engine/session setup.

Dev/test: SQLite (DATABASE_URL default) — zero external infra needed.
Prod: Postgres + PostGIS. Swap DATABASE_URL and nothing else in app code
changes, because geometry columns below are conditionally enabled only
when the dialect is postgresql (see models.py).
"""
import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("uzhavan.database")

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

# pool_pre_ping: transparently discards/reconnects dead connections (e.g.
# after a DB restart) instead of surfacing a stale-connection error on the
# next request.
engine = create_engine(
    settings.DATABASE_URL, connect_args=connect_args, future=True, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    """Block until the database accepts a real connection, retrying on a
    fixed delay.

    Docker Compose's own healthcheck + depends_on already keeps this
    container from starting until Postgres reports healthy — but that
    ordering guarantee doesn't hold everywhere this app might run (a plain
    `docker run`, some PaaS platforms, a developer's local Postgres that's
    still coming up). Retrying here means a database that becomes ready a
    few seconds late is a short log message, not a crashed container that
    a health check then waits on forever.
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect():
                if attempt > 1:
                    logger.info("Database connection established (attempt %s).", attempt)
                return
        except OperationalError as exc:
            last_error = exc
            logger.warning(
                "Database not ready yet (attempt %s/%s) — retrying in %.0fs...",
                attempt, max_attempts, delay_seconds,
            )
            time.sleep(delay_seconds)
    raise RuntimeError(
        f"Could not connect to the database after {max_attempts} attempts "
        f"({max_attempts * delay_seconds:.0f}s). Last error: {last_error}"
    )


def init_db():
    """Create tables. Fine for dev; production should use Alembic migrations
    (see backend/alembic/) instead of calling this."""
    import app.models  # noqa: F401 ensure models are registered
    Base.metadata.create_all(bind=engine)

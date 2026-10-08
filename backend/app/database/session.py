import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

log = logging.getLogger("cloudsentry.db")


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    """Render/Heroku style URLs start with postgres://, SQLAlchemy needs a driver name."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


_url = normalize_url(settings.db_url)
_kwargs: dict = {"pool_pre_ping": True}
if _url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
else:
    _kwargs["connect_args"] = {"connect_timeout": 5}
    _kwargs.update(pool_size=5, max_overflow=5, pool_recycle=1800)

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
_ready = False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_ready() -> bool:
    return _ready


def init_db(retries: int = 3) -> None:
    """Create tables (empty database is fine) and bootstrap users, rules and demo data."""
    global _ready
    from app.models import tables  # noqa: F401  (registers models)
    from app.services import bootstrap

    for attempt in range(retries):
        try:
            Base.metadata.create_all(engine)
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.5)  # two instances may race to create tables
    with SessionLocal() as db:
        bootstrap.run(db)
    _ready = True
    log.info("Database ready (%s)", engine.dialect.name)


def check_db() -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, round((time.perf_counter() - start) * 1000, 1)
    except Exception:
        return False, round((time.perf_counter() - start) * 1000, 1)

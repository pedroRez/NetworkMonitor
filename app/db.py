import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

load_dotenv(encoding="utf-8-sig")

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/network_monitor",
)

connect_args: dict[str, str] = {}
if DATABASE_URL.startswith("postgresql"):
    client_encoding = os.getenv("DB_CLIENT_ENCODING", "UTF8")
    connect_args["options"] = f"-c client_encoding={client_encoding}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _safe_database_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<invalid DATABASE_URL>"


def test_db_connection() -> None:
    safe_url = _safe_database_url(DATABASE_URL)
    logger.info("Testing database connection: %s", safe_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        detail = getattr(exc, "orig", None)
        if detail is not None:
            logger.error("Database error type: %s", type(detail).__name__)
            logger.error("Database error detail: %r", detail)
            logger.error("Database error args: %s", getattr(detail, "args", None))
            pgerror = getattr(detail, "pgerror", None)
            if pgerror:
                logger.error("Database pgerror: %s", pgerror)
        logger.error("Database exception args: %s", getattr(exc, "args", None))
        logger.exception("Database connection failed: %s", safe_url)
        raise
    logger.info("Database connection OK: %s", safe_url)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

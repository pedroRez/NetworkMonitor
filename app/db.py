import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

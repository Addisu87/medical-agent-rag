from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logfire
from app.db.models import Base


# Database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    echo=True,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Check connection health
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database health check
def check_db_health():
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        return True
    except Exception as e:
        logfire.error(f"Database health check failed: {e}")
        return False


# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)
    with logfire.span("init_database"):
        logfire.info("Database tables created successfully")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config.settings import settings

# Check if we are running with SQLite (often used for testing/local runs)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create engine
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Async session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# Dependency injection for FastAPI db sessions
async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

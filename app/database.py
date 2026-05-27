from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config.settings import settings

import ssl
import urllib.parse

# Check if we are running with SQLite (often used for testing/local runs)
db_url = settings.DATABASE_URL.strip("'\"")

# Automatically URL-encode the password if it contains '@' (common in Supabase passwords)
if "@" in db_url:
    parts = db_url.split("://", 1)
    if len(parts) == 2:
        protocol, rest = parts
        if "@" in rest:
            cred, host = rest.rsplit("@", 1)
            if ":" in cred:
                user, password = cred.split(":", 1)
                # Only encode if it contains '@' to prevent double-encoding
                if "@" in password:
                    password = urllib.parse.quote_plus(password)
                db_url = f"{protocol}://{user}:{password}@{host}"

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

is_sqlite = db_url.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False
else:
    # Configure custom SSL context to bypass verification errors with self-signed certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

engine_args = {
    "connect_args": connect_args,
    "echo": False
}

# Connection pool tuning optimized for serverless environments (like Vercel)
if not is_sqlite:
    engine_args.update({
        "pool_size": 2,
        "max_overflow": 0,
        "pool_recycle": 1800,
        "pool_pre_ping": True
    })

# Create engine
engine = create_async_engine(
    db_url,
    **engine_args
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

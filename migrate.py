import asyncio
import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

from app.models.ticket import Ticket
from app.models.note import Note
from app.database import Base

# Load .env file
load_dotenv()

SQLITE_URL = "sqlite+aiosqlite:///./tickets.db"

async def migrate():
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url:
        print("DATABASE_URL not found in environment or .env file.")
        return
    postgres_url = postgres_url.strip("'\"")

    # Automatically URL-encode the password if it contains '@'
    if "@" in postgres_url:
        parts = postgres_url.split("://", 1)
        if len(parts) == 2:
            protocol, rest = parts
            if "@" in rest:
                cred, host = rest.rsplit("@", 1)
                if ":" in cred:
                    user, password = cred.split(":", 1)
                    if "@" in password:
                        password = urllib.parse.quote_plus(password)
                    postgres_url = f"{protocol}://{user}:{password}@{host}"

    # Ensure async driver protocol is used
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"Connecting to SQLite: {SQLITE_URL}")
    sqlite_engine = create_async_engine(SQLITE_URL)
    sqlite_session = async_sessionmaker(sqlite_engine, expire_on_commit=False, class_=AsyncSession)

    print("Connecting to Supabase Postgres...")
    pg_engine = create_async_engine(postgres_url)
    pg_session = async_sessionmaker(pg_engine, class_=AsyncSession)

    # 1. Read SQLite data
    async with sqlite_session() as s_sess:
        print("Fetching tickets from SQLite...")
        result = await s_sess.execute(select(Ticket))
        tickets = result.scalars().all()
        print(f"Found {len(tickets)} tickets in SQLite.")

        print("Fetching notes from SQLite...")
        result = await s_sess.execute(select(Note))
        notes = result.scalars().all()
        print(f"Found {len(notes)} notes in SQLite.")

    # 2. Create tables in Supabase Postgres if they do not exist
    print("Ensuring tables are initialized in Supabase...")
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

from datetime import timezone

    # 3. Write data to Supabase Postgres
    async with pg_session() as p_sess:
        print("Inserting records into Supabase...")
        
        # Add tickets
        for t in tickets:
            t_created = t.created_at.replace(tzinfo=timezone.utc) if t.created_at and t.created_at.tzinfo is None else t.created_at
            t_updated = t.updated_at.replace(tzinfo=timezone.utc) if t.updated_at and t.updated_at.tzinfo is None else t.updated_at
            new_t = Ticket(
                ticket_id=t.ticket_id,
                customer_name=t.customer_name,
                customer_email=t.customer_email,
                subject=t.subject,
                description=t.description,
                status=t.status,
                created_at=t_created,
                updated_at=t_updated
            )
            p_sess.add(new_t)
            
        # Add notes
        for n in notes:
            n_created = n.created_at.replace(tzinfo=timezone.utc) if n.created_at and n.created_at.tzinfo is None else n.created_at
            new_n = Note(
                ticket_id=n.ticket_id,
                note_text=n.note_text,
                created_at=n_created
            )
            p_sess.add(new_n)

        await p_sess.commit()
        print(f"Migration completed successfully! Migrated {len(tickets)} tickets and {len(notes)} notes.")

    # Close engines
    await sqlite_engine.dispose()
    await pg_engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())

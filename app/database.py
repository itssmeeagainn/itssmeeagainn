from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from databases import Database
from .config import settings
import asyncio

# Synchronous database setup
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous database setup for better performance
if settings.database_url.startswith("sqlite"):
    async_database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    async_engine = create_async_engine(
        async_database_url,
        echo=settings.debug
    )
else:
    async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug
    )

AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Database instance for direct async queries
database = Database(async_database_url)


def get_db() -> Session:
    """Get synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Get asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Initialize database connection."""
    await database.connect()


async def close_database():
    """Close database connection."""
    await database.disconnect()


# Database utilities
async def create_tables():
    """Create all database tables."""
    from .models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    from .models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_database_connection():
    """Check if database connection is working."""
    try:
        await database.fetch_one("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
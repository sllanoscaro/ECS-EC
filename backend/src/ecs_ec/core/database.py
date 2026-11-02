"""PostgreSQL async engine/session factory and shared declarative metadata."""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common metadata with stable constraint names for migration review."""

    metadata = MetaData(naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    })


class Database:
    """Own engine/pool resources; sessions require explicit producer transactions."""

    def __init__(self, url: str):
        """Create a lazy Psycopg async pool; credentials must never be logged."""
        self.engine = create_async_engine(
            url, pool_pre_ping=True, hide_parameters=True,
            connect_args={"options": "-c timezone=UTC", "connect_timeout": 5},
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def close(self) -> None:
        """Dispose pool connections during shutdown or after a test."""
        await self.engine.dispose()

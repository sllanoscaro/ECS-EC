"""Producer-owned transactions; writers never commit independently."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    """One async session per context; rollback unless the producer explicitly commits."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        """Receive the pool-backed factory without opening a connection."""
        self.sessions = sessions
        self.session: AsyncSession

    async def __aenter__(self):
        """Open a new session for this transaction; return the unit of work."""
        self.session = self.sessions()
        return self

    async def commit(self) -> None:
        """Commit result and evidence atomically; propagate database errors to the producer."""
        await self.session.commit()

    async def __aexit__(self, exc_type, exc, traceback):
        """Rollback outstanding work, including cancellation, and always release resources."""
        try:
            await self.session.rollback()
        finally:
            await self.session.close()

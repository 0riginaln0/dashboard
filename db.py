import asyncio
import aiosqlite
from contextlib import asynccontextmanager


async def get_connection(db_path: str):
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    return conn


class WriterProvider:
    def __init__(self, connection: aiosqlite.Connection):
        self._connection = connection
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self):
        await self._lock.acquire()
        try:
            yield self._connection
        finally:
            self._lock.release()


class ReaderProvider:
    def __init__(self, connections):
        self._pool = asyncio.Queue()
        for conn in connections:
            self._pool.put_nowait(conn)

    @asynccontextmanager
    async def acquire(self):
        conn = await self._pool.get()
        try:
            yield conn
        finally:
            await self._pool.put(conn)

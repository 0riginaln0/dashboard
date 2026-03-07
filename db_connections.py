import aiosqlite
import asyncio
from aiosqlite import Connection


async def get_connection(db_path: str):
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    return conn


async def setup_database(writer: WriterProvider):
    """Initialize schema and enable WAL."""
    async with writer as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.commit()


async def writer_task(writer: WriterProvider):
    """Example writer that inserts data."""
    async with writer as conn:
        for i in range(10):
            print("before execute", conn.in_transaction)
            await conn.execute("INSERT INTO data (value) VALUES (?)", (f"item_{i}",))
            print("after execute", conn.in_transaction)
            await conn.commit()
            print("after commit", conn.in_transaction)
            print(f"Writer committed {i}")


async def reader_task(conn: Connection, reader_id):
    """Example reader that queries data."""
    for _ in range(10):
        async with conn.execute("SELECT * FROM data") as cursor:
            rows = await cursor.fetchall()
            print(f"Reader {reader_id} sees {rows} rows")


class WriterProvider:
    def __init__(self, connection: aiosqlite.Connection):
        self._connection = connection
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()


async def main():
    writer_conn = await get_connection("mydb.sqlite")
    writer = WriterProvider(writer_conn)
    await setup_database(writer)
    readers = [await get_connection("mydb.sqlite") for _ in range(3)]

    try:
        await asyncio.gather(
            writer_task(writer),
            *[reader_task(reader, i) for i, reader in enumerate(readers)],
        )
    finally:
        await writer_conn.close()
        for reader_conn in readers:
            await reader_conn.close()


if __name__ == "__main__":
    asyncio.run(main())

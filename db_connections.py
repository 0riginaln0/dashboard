import aiosqlite
import asyncio
from aiosqlite import Connection


async def get_connection(db_path: str):
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    return conn


async def setup_database(writer: Connection):
    """Initialize schema and enable WAL."""
    await writer.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY,
            value TEXT
        )
    """)
    await writer.commit()


async def writer_task(writer: Connection):
    """Example writer that inserts data."""
    for i in range(10):
        await writer.execute("INSERT INTO data (value) VALUES (?)", (f"item_{i}",))
        await writer.commit()
        print(f"Writer committed {i}")


async def reader_task(reader: Connection, reader_id):
    """Example reader that queries data."""
    for _ in range(10):
        async with reader.execute("SELECT * FROM data") as cursor:
            rows = await cursor.fetchall()
            print(f"Reader {reader_id} sees {rows} rows")


async def main():
    # Create one writer connection
    writer = await get_connection("mydb.sqlite")
    await setup_database(writer)
    readers = [await get_connection("mydb.sqlite") for _ in range(3)]

    try:
        # Run writer and readers concurrently
        await asyncio.gather(
            writer_task(writer),
            *[reader_task(reader, i) for i, reader in enumerate(readers)],
        )
    finally:
        # Clean up all connections
        await writer.close()
        for reader in readers:
            await reader.close()


if __name__ == "__main__":
    asyncio.run(main())

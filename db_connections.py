import asyncio
from db import get_connection, WriterProvider, ReaderProvider


async def setup_database(writer: WriterProvider):
    """Initialize schema and enable WAL."""
    async with writer.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.commit()


async def writer_task(writer: WriterProvider):
    """Example writer that inserts data."""
    async with writer.acquire() as conn:
        for i in range(10):
            print("before execute", conn.in_transaction)
            await conn.execute("INSERT INTO data (value) VALUES (?)", (f"item_{i}",))
            print("after execute", conn.in_transaction)
            await conn.commit()
            print("after commit", conn.in_transaction)
            print(f"Writer committed {i}")


async def reader_task(reader_provider: ReaderProvider, reader_id):
    for _ in range(10):
        async with reader_provider.acquire() as conn:
            async with conn.execute("SELECT * FROM data") as cursor:
                rows = await cursor.fetchall()
                print(f"Reader {reader_id} sees {rows} rows")


async def main():
    writer_conn = await get_connection("mydb.sqlite")
    writer_provider = WriterProvider(writer_conn)
    await setup_database(writer_provider)
    reader_conns = [await get_connection("mydb.sqlite") for _ in range(3)]
    reader_provider = ReaderProvider(reader_conns)

    try:
        await asyncio.gather(
            writer_task(writer_provider),
            *[reader_task(reader_provider, i) for i in range(3)],
        )
    finally:
        await writer_conn.close()
        for reader_conn in reader_conns:
            await reader_conn.close()


if __name__ == "__main__":
    asyncio.run(main())

# stdlib
import os
import json
import asyncio
import mimetypes
from datetime import datetime
from textwrap import dedent

# third-party
import aiosql
import aiofiles
from micropie import App
import uvicorn

# local
from db import get_connection, WriterProvider, ReaderProvider


class Root(App):
    def __init__(self):
        super().__init__()
        self.clients: set[asyncio.Queue[datetime]] = set()

    async def _setup_db(self):
        self.queries = aiosql.from_path("./sql/queries.sql", "aiosqlite")

        DB_NAME = "foo.db"
        READERS_CONNECTIONS_COUNT = 3

        self._writer_conn = await get_connection(DB_NAME)
        self.db_writer = WriterProvider(self._writer_conn)

        self._reader_conns = [
            await get_connection(DB_NAME) for _ in range(READERS_CONNECTIONS_COUNT)
        ]
        self.db_reader = ReaderProvider(self._reader_conns)

    async def _close_db(self):
        await self._writer_conn.close()
        for reader_conn in self._reader_conns:
            await reader_conn.close()

    async def _startup(self):
        await self._setup_db()
        self.broadcast_task = asyncio.create_task(self._broadcast_time())

    async def _shutdown(self):
        await self._close_db()
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

    async def _broadcast_time(self):
        try:
            while True:
                await asyncio.sleep(1)
                now = datetime.now()
                for queue in list(self.clients):
                    try:
                        await queue.put(now)
                    except Exception:
                        self.clients.discard(queue)
        except asyncio.CancelledError:
            pass

    async def _serve_file(self, base_dir, path):
        # Normalize the file path to prevent directory traversal
        file_path = os.path.normpath(os.path.join(base_dir, path))
        # Ensure the path stays within the specified directory
        base_dir = os.path.normpath(base_dir)
        if not file_path.startswith(base_dir):
            return 403, "Forbidden", []

        if os.path.exists(file_path):
            # Determine the appropriate Content-Type based on file extension
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

            # Stream the file content to reduce memory usage
            async def stream_file():
                async with aiofiles.open(file_path, "rb") as f:
                    while chunk := await f.read(65536):  # Read in 64KB chunks
                        yield chunk

            return 200, stream_file(), [("Content-Type", content_type)]
        return 404, "Not Found", []

    async def _views(self, path):
        return await self._serve_file("views", path)

    async def static(self, path):
        return await self._serve_file("static", path)

    async def index(self):
        return await self._render_template(
            "index.html", time=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        )

    async def sse(self):
        return await self._views("sse.html")

    async def sse_endpoint(self):
        async def generator():
            queue: asyncio.Queue[datetime] = asyncio.Queue()
            self.clients.add(queue)
            queue.put_nowait(datetime.now())

            try:
                while True:
                    now = await queue.get()
                    html_content = dedent(f"""\
                                           <h2>Server Response</h2>
                                           <p>Time: {now.strftime("%Y-%m-%d %H:%M:%S.%f")}</p>
                                           """)
                    event_data = {
                        "target": "#data-container",
                        "swap": "innerMorph",
                        "text": html_content,
                    }
                    yield f"event: fixi\ndata: {json.dumps(event_data)}\n\n"
            except asyncio.CancelledError:
                print("Client disconnected")
            finally:
                self.clients.discard(queue)

        return (
            200,
            generator(),
            [
                ("Content-Type", "text/event-stream"),
                ("Cache-Control", "no-cache"),
                ("Connection", "keep-alive"),
            ],
        )

    async def poll(self):
        return await self._views("poll.html")

    async def poll_endpoint(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return dedent(f"""\
                       <h2>Server Response</h2>
                       <p>Time: {current_time}</p>
                       """)


app = Root()
app.startup_handlers.append(app._startup)
app.shutdown_handlers.append(app._shutdown)


async def main():
    config = uvicorn.Config("app:app")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

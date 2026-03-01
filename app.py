import os
import json
import asyncio
import mimetypes
from datetime import datetime

import pugsql
import aiofiles
from micropie import App


class Root(App):
    def __init__(self):
        super().__init__()
        self.clients: set[asyncio.Queue[datetime]] = set()
        self.broadcast_task = None

    async def _startup(self):
        self.broadcast_task = asyncio.create_task(self._broadcast_time())
        self.queries = pugsql.module("sql")
        self.queries.connect("sqlite:///foo.db")

    async def _shutdown(self):
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        self.queries.disconnect()

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

    async def _views(self, path):
        file_path = os.path.normpath(os.path.join("views", path))
        views_dir = os.path.normpath("views")
        if not file_path.startswith(views_dir):
            return 403, "Forbidden", []

        if os.path.exists(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

            async def stream_file():
                async with aiofiles.open(file_path, "rb") as f:
                    while chunk := await f.read(65536):
                        yield chunk

            return 200, stream_file(), [("Content-Type", content_type)]
        return 404, "Not Found", []

    async def static(self, path):
        # Normalize the file path to prevent directory traversal
        file_path = os.path.normpath(os.path.join("static", path))
        # Ensure the path stays within the 'static' directory
        static_dir = os.path.normpath("static")
        if not file_path.startswith(static_dir):
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
            await queue.put(datetime.now())

            try:
                while True:
                    now = await queue.get()
                    html_content = f"""
                    <h2>Server Response</h2>
                    <p>Time: {now.strftime("%Y-%m-%d %H:%M:%S.%f")}</p>
                    """
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
        return f"""
        <h2>Server Response</h2>
        <p>Time: {current_time}</p>
        """


app = Root()
app.startup_handlers.append(app._startup)
app.shutdown_handlers.append(app._shutdown)

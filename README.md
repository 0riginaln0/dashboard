# Demo

![A screen record showing several tabs opened with SSE connections, which are updated synchronously, two polling tabs and one tab with templated page](demo.gif)

## How to start things up:

```sh
# uv python install <version>
uv sync
uv run app.py
```

## Dependencies

Web framework:
- [MicroPie](https://github.com/patx/micropie)

Database access:
- [aoisql](https://github.com/nackjicholson/aiosql)

Frontend things:
- [fixi.js](https://github.com/bigskysoftware/fixi)
- [_hyperscript](https://github.com/bigskysoftware/_hyperscript)
- [Idiomorph](https://github.com/bigskysoftware/idiomorph)

Miscellaneous:
- [Phoenix PubSub](https://github.com/0riginaln0/phoenix-pubsub)

## Development

Package & Project manager:
- https://docs.astral.sh/uv/

Database browser:
- https://sqlitestudio.pl/

Recommended VSCode extensions:
- https://marketplace.visualstudio.com/items?itemName=dz4k.vscode-hyperscript-org
- https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff
- https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter
- https://marketplace.visualstudio.com/items?itemName=ms-python.python
- https://marketplace.visualstudio.com/items?itemName=qwtel.sqlite-viewer
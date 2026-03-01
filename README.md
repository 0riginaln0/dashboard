## How to start things up:

```sh
# uv python install <version>
uv sync
uvicorn app:app
```

F5 (Debug: Start Debugging) in VSCode.

## Dependencies

Web framework:
- [MicroPie](https://github.com/patx/micropie)

Database access:
- [PugSQL](https://github.com/mcfunley/pugsql)

Frontend things:
- [fixi.js](https://github.com/bigskysoftware/fixi)
- [_hyperscript](https://github.com/bigskysoftware/_hyperscript)
- [Idiomorph](https://github.com/bigskysoftware/idiomorph)

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
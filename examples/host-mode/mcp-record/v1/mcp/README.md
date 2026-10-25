# unit-desk

A small MCP (Model Context Protocol) server over stdio for unit conversion and calendar day counts. Python standard library only.

## Tools

- **convert_units** — length, mass, temperature, and volume; rejects conversions across different kinds (e.g. km → kg).
- **days_between** — whole days between two ISO dates (`YYYY-MM-DD`); negative if `end` is before `start`.

## Install

From this folder’s parent directory (or any host that supports MCP):

```bash
proofhouse install mcp unit-desk --command=python --arg=server.py --into <host>
```

Point the host’s working directory at this folder, or copy `server.py` and run with `python server.py`.

## Manual test

```bash
cd examples/host-mode/mcp
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | python server.py
```

Send one JSON-RPC object per line on stdin; read replies from stdout only.

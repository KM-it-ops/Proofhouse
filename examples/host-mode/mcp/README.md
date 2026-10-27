# unit-desk

A small MCP (Model Context Protocol) server over stdio for unit conversion and calendar day counts. Python standard library only.

## Tools

- **convert_units** — length, mass, temperature, and volume; rejects conversions across different kinds (e.g. km → kg).
- **days_between** — whole days between two ISO dates (`YYYY-MM-DD`); negative if `end` is before `start`.

## Install

```bash
proofhouse install mcp unit-desk --command=python --arg="<full path to this folder>/server.py" --into <host>
```

Replace `<full path to this folder>` with the full path of the folder that holds this README. The host starts the server from its own folder, so a bare `server.py` would not be found. Keep the double quotes; they let a path with spaces work.

## Manual test

```bash
cd examples/host-mode/mcp
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | python server.py
```

Send one JSON-RPC object per line on stdin; read replies from stdout only.

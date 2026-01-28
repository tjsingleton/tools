# carrier-api

CLI for poking the Carrier API from a repeatable folder.

Default behavior is **dry-run** (prints a `curl` command). Use `--execute` to make the request.

## Setup

Env vars:

- `CARRIER_API_BASE_URL` (example: `https://api.example.com`)
- `CARRIER_API_TOKEN` (bearer token)

## Examples

Dry-run:

```bash
python ../../scripts/run_tool.py carrier-api -- --path /v1/me
```

Execute:

```bash
python ../../scripts/run_tool.py carrier-api -- --execute --path /v1/me
```

POST with JSON:

```bash
python ../../scripts/run_tool.py carrier-api -- --execute --method POST --path /v1/foo --json '{"a":1}'
```


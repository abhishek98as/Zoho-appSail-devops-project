# Flask Webhook on Zoho Catalyst AppSail — End‑to‑End Guide

This guide explains how this Flask webhook app is structured, how to run it locally, and how to deploy and operate it on Zoho Catalyst AppSail. It’s written for beginners through intermediate developers.

## What you get

- Minimal Flask app with three endpoints:
  - GET `/health` → returns `ok`
  - GET `/webhook?challenge=...` → echoes challenge for verification
  - POST `/webhook` → accepts JSON, appends to a log file (for demo)
- Production startup using gunicorn on AppSail
- Postman collection and environments for quick testing

## Prerequisites

- Windows/macOS/Linux
- Python 3.9+ for local runs
- Node.js 14+ and npm for Catalyst CLI
- A Zoho account with access to Zoho Catalyst

Verify locally:

```pwsh
python --version
node --version
npm --version
```

Install Catalyst CLI:

```pwsh
npm install -g zcatalyst-cli
catalyst --version
```

## Repository layout

```
/ (root)
  main.py                 # Flask app (root copy for local dev)
  requirements.txt        # Python deps for local dev
  Procfile                # Optional; not used by AppSail when app-config.json exists
  postman/                # Postman collection + environments
  appsail-python/         # AppSail service source
    main.py               # Flask app used in AppSail deployment
    requirements.txt      # Flask + gunicorn for container
    app-config.json       # AppSail configuration (startup command, runtime)
  docs/
    APPSAIL_FLASK_GUIDE.md
```

Notes:

- AppSail runs from `appsail-python/`, not the root by default. Make edits there for deploys.
- Avoid committing virtualenvs or OS caches. The `.gitignore` already excludes common artifacts.

## Endpoints

- GET `/health` → 200 "ok"
- GET `/webhook?hub.challenge=123` or `?challenge=123` → 200 "123"
- POST `/webhook` → 200 `{ "status": "ok" }`

In production, writing to the current directory may be restricted. If you need to write files at runtime, prefer the OS temp dir (e.g., `/tmp` on Linux) or use Catalyst services (Data Store/Object Storage).

## Run locally

```pwsh
# (Optional) Create a venv
python -m venv .venv
. .venv/Scripts/Activate.ps1

# Install deps
pip install -r requirements.txt

# Run the app
$env:PORT=5000
python .\main.py
```

Test locally:

```pwsh
Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -Method GET
Invoke-RestMethod -Uri "http://127.0.0.1:5000/webhook?challenge=123" -Method GET
Invoke-RestMethod -Uri "http://127.0.0.1:5000/webhook" -Method POST -ContentType "application/json" -Body '{"hello":"world"}'
```

## Postman collection

- Import `postman/Webhook.postman_collection.json`
- Environments:
  - `postman/Webhook.postman_environment.json` (Local)
  - `postman/Webhook-Catalyst.postman_environment.json` (Deployed URL)

Run the three requests to validate health, challenge echo, and POST.

## Catalyst CLI login

```pwsh
catalyst login
# If you have multiple orgs/projects, you can set them later with:
# catalyst project:list
# catalyst project:use <name_or_id> --org <org_id>
```

## AppSail options
You can deploy in two ways:

1) Regular AppSail (initialized) — recommended
- The directory `appsail-python/` contains:
  - `main.py` (Flask `app`)
  - `requirements.txt` (Flask + gunicorn)
  - `app-config.json` (runtime, command)
- The project root has `catalyst.json` with the AppSail resource entry.

Deploy:

```pwsh
# From the project root
catalyst deploy appsail
```

2) Standalone deploy — quick one-off
- From a Catalyst project root (`catalyst.json` present) where your build files live, run:
```pwsh
catalyst deploy appsail
# Follow prompts: name, build path (select appsail-python), runtime (Python 3), startup command
```

## Startup command (critical)
AppSail executes the startup command directly (no shell). If you need shell features such as `&&` and env var expansion, wrap it with `sh -c`.

Final command we use:
```text
sh -c "python3 -m pip install --no-cache-dir -r requirements.txt && python3 -m gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$X_ZOHO_CATALYST_LISTEN_PORT main:app"
```

Why:

- Installs Python deps inside the Linux container at startup (ensures correct wheels)
- Runs gunicorn, binding to the Catalyst listen port via env var `X_ZOHO_CATALYST_LISTEN_PORT`
- Uses `sh -c` so `&&` and `$VAR` expansion work (per AppSail docs)

Where to configure:

- In `appsail-python/app-config.json` under `command`, or
- In Console: AppSail → Your Service → Configuration → Startup Command

Example `app-config.json` (essential parts):
```json
{
  "stack": "python_3_9",
  "build_path": "./",
  "memory": 256,
  "env_variables": {},
  "command": "sh -c \"python3 -m pip install --no-cache-dir -r requirements.txt && python3 -m gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$X_ZOHO_CATALYST_LISTEN_PORT main:app\""
}
```

## Verify the deployment
After a successful `catalyst deploy appsail`, note the URL shown in the CLI.

```pwsh
# Replace with your AppSail URL
$base = "https://<appsail-name>-<zaid>.development.catalystappsail.in"
Invoke-RestMethod -Uri "$base/health" -Method GET -TimeoutSec 30
Invoke-RestMethod -Uri "$base/webhook?challenge=123" -Method GET -TimeoutSec 30
Invoke-RestMethod -Uri "$base/webhook" -Method POST -ContentType "application/json" -Body '{"hello":"world"}' -TimeoutSec 30
```

## Troubleshooting
- HTTP 500 JSON from AppSail (no app logs visible):
  - Common causes:
    - App not listening on `X_ZOHO_CATALYST_LISTEN_PORT`
    - Startup command not using a shell (env var not expanded; `&&` ignored)
    - Missing dependencies (Windows wheels copied into source, incompatible with Linux)
  - Fixes:
    - Use the `sh -c "...$X_ZOHO_CATALYST_LISTEN_PORT..."` startup command as above
    - Ensure `main.py` exposes `app = Flask(__name__)`
    - Do NOT commit vendored packages/`site-packages` into the source; let `pip install` run in container

- How to view logs:
  - Console → AppSail → Your app → Instances → Logs
  - Use these logs to confirm install and server start line (gunicorn binding)

- File writes:
  - AppSail restricts writes to the current directory. Prefer `/tmp` or Catalyst Data Store/Object Storage for persistence.

- Memory/runtime:
  - Start with `memory: 256`. Increase if app is large or CPU-bound.
  - Stack `python_3_9` matches the sample; use the Console to adjust if needed.

## Updating the app
1) Edit `appsail-python/main.py` or `appsail-python/requirements.txt`
2) Deploy:
```pwsh
catalyst deploy appsail
```
3) Verify `/health` again

## Security tips
- Validate webhook sources (shared secret / HMAC)
- Avoid logging sensitive data
- Rate-limit and add request size limits
- Rotate secrets via AppSail environment variables (configure in Console or `app-config.json`)

## Appendix: curl equivalents (bash)
```bash
# Health
curl -sS "$BASE/health"
# Challenge
curl -sS "$BASE/webhook?challenge=123"
# POST
curl -sS -X POST "$BASE/webhook" -H 'Content-Type: application/json' -d '{"hello":"world"}'
```

---
If you need a “one-command” re-deploy checklist: update code → `catalyst deploy appsail` → test `/health` → test `/webhook`.

# Flask Webhook on Zoho Catalyst (AppSail)

This repo hosts a minimal Flask webhook app ready for deployment to Zoho Catalyst AppSail.

## Endpoints
- GET `/health` -> returns `ok` (health check)
- GET `/webhook` -> echoes challenge param (`hub.challenge`/`challenge`/`challange`) for verification
- POST `/webhook` -> accepts JSON payload, appends to `webhook.txt`, returns `{ "status": "ok" }`

## Local Run

```pwsh
# Create venv (optional)
python -m venv .venv
. .venv/Scripts/Activate.ps1

pip install -r requirements.txt
$env:PORT=5000
python main.py
```

## Deploy to Zoho Catalyst (summary)

Follow the PDF guide in this workspace. High level steps for AppSail:

1. Ensure `requirements.txt` and `Procfile` are present (they are).
2. Zip the app contents (avoid .venv and __pycache__).
3. In Catalyst Console, create an AppSail service and upload the zip.
4. Catalyst installs dependencies and starts with `gunicorn` using `Procfile`.
5. Note the public URL; set it as your webhook endpoint.

If you need help with CLI-based deploy or environment variables, ask and we can wire them up.

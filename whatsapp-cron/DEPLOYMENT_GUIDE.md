# WhatsApp Status Sync Service - Deployment Guide

This guide provides instructions for deploying the WhatsApp Status Sync Service to Zoho Catalyst AppSail.

## Prerequisites

1. Zoho Catalyst CLI installed: `npm install -g @zoho/catalyst-cli`
2. Zoho Developer account with access to the Whatsapp-Cron project (Project ID: 6751000000139181)
3. Logged in to Catalyst CLI: `catalyst login`

## Deployment Steps

### 1. Verify Project Structure

Ensure your project directory contains the following files:
- `app.py` - Entry point wrapper
- `main.py` - Core application logic
- `requirements.txt` - Python dependencies
- `app-config.json` - AppSail configuration
- `catalyst.json` - Project configuration

### 2. Deploy to AppSail

```bash
# Navigate to the project directory
cd whatsapp-cron

# Deploy to AppSail
catalyst deploy appsail
```

### 3. Verify Deployment

After deployment completes, verify the service is running:

```bash
# Check deployment status
catalyst status appsail

# View application logs
catalyst logs appsail
```

Visit the application URL to verify it's running:
- Base URL: `https://whatsapp-cron-XXXXX.development.catalystappsail.in/`
- Health check: `https://whatsapp-cron-XXXXX.development.catalystappsail.in/health`

## Configuration Parameters

The service is configured with the following parameters that can be modified in `main.py`:

```python
# Webhook API configuration
WEBHOOK_API_URL = "https://test-knight-50030314031.development.catalystappsail.in/webhook/master"
WEBHOOK_API_CREDENTIALS = {
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
}

# Zoho authentication configuration
ZOHO_AUTH_PARAMS = {
    "refresh_token": "1000.abe42f5ee32cbd2f51f4f2996c1a081b.49d7de9ca65bc657dac4d5dfaec9507c",
    "client_id": "1000.09GO95AZNVR8RZ24MU799Y4HVFOIFP",
    "client_secret": "24d22886c8d171fbb7210453bf3e2644ae4030bbf0",
    "grant_type": "refresh_token"
}

# Batch processing configuration
BATCH_SIZE = 100  # Number of records to process in one batch
SYNC_INTERVAL = 10 * 60  # 10 minutes in seconds
```

## Monitoring

Monitor the service using the following endpoints:

1. **Health Check**:
   ```
   GET /health
   ```
   Response:
   ```json
   {
     "status": "ok",
     "last_sync": "2023-09-01T12:34:56.789012",
     "sync_in_progress": false
   }
   ```

2. **Sync Status**:
   ```
   GET /sync/status
   ```
   Response:
   ```json
   {
     "sync_in_progress": false,
     "last_sync_time": "2023-09-01T12:34:56.789012",
     "stats": {
       "total_records_fetched": 150,
       "records_updated": 120,
       "records_not_found": 30,
       "errors": 0,
       "last_run": "2023-09-01T12:34:56.789012",
       "duration": 45.67
     }
   }
   ```

3. **Trigger Manual Sync**:
   ```
   POST /sync/trigger
   ```
   Response:
   ```json
   {
     "status": "ok",
     "message": "Sync triggered"
   }
   ```

## Troubleshooting

### Common Issues

1. **Sync Not Running**
   - Check application logs: `catalyst logs appsail`
   - Verify the scheduler thread started successfully
   - Try triggering a manual sync: `POST /sync/trigger`

2. **Authentication Errors**
   - Verify the refresh token is valid
   - Check client ID and secret are correct
   - Examine logs for authentication errors

3. **Webhook API Connection Issues**
   - Verify the webhook API URL is correct
   - Check webhook API credentials
   - Test the webhook API directly

4. **Performance Issues**
   - Adjust batch size in `main.py`
   - Modify sync interval if needed
   - Check for rate limiting in Zoho Creator API

### Viewing Logs

```bash
# View recent logs
catalyst logs appsail

# View logs with timestamps
catalyst logs appsail --timestamps

# Follow logs in real-time
catalyst logs appsail --follow
```

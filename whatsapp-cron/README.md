# WhatsApp Status Sync Service

This service synchronizes WhatsApp message statuses between a webhook database and Zoho Creator.

## Features

- Automatically syncs message statuses every 10 minutes
- Processes records in batches to handle large volumes efficiently
- Refreshes Zoho authentication token automatically
- Provides API endpoints for monitoring and manual triggering
- Handles errors gracefully with comprehensive logging

## API Endpoints

- `/` - Basic health check
- `/health` - Detailed health status
- `/sync/status` - Current sync statistics
- `/sync/trigger` - Manually trigger a sync (POST)

## Deployment

Deploy to Zoho Catalyst AppSail:

```bash
catalyst deploy appsail
```

## Configuration

The service is configured with the following parameters:

- Sync interval: 10 minutes
- Batch size: 100 records per batch
- Token refresh: Automatic (with 5-minute safety buffer)

## Architecture

1. **Authentication**: Obtains and manages Zoho access tokens
2. **Data Fetching**: Retrieves queued messages from Zoho Creator
3. **Status Lookup**: Queries webhook database for message statuses
4. **Status Update**: Updates Zoho Creator records with current statuses
5. **Scheduling**: Runs the sync process at regular intervals

## Monitoring

Monitor the service using the `/sync/status` endpoint which provides:
- Total records processed
- Records updated
- Records not found
- Error count
- Last run time
- Sync duration

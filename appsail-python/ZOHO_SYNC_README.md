# Zoho WhatsApp Status Synchronization

## Quick Start

The Zoho synchronization feature has been successfully implemented. It automatically syncs WhatsApp message statuses from your webhook data to Zoho Creator every 60 minutes.

## What's New

1. **Automatic Scheduler**: Runs every 60 minutes without manual intervention
2. **Efficient Processing**: Only processes records that haven't been synced yet
3. **Concurrent Updates**: Processes 10 records simultaneously for faster syncing
4. **Database Optimization**: Added "Updated" column to track synced records
5. **Error Handling**: Robust error handling with retry logic

## Key Files

- `main.py`: Updated with Zoho sync integration
- `zoho_sync_scheduler.py`: New scheduler implementation
- `test_zoho_sync.py`: Test script to verify functionality
- `ZOHO_SYNC_DOCUMENTATION.md`: Detailed documentation

## How It Works

1. **Every 60 minutes**, the scheduler:
   - Refreshes Zoho access token if needed
   - Fetches up to 1000 non-delivered records from Zoho
   - Looks up latest status in your webhook database
   - Updates Zoho records with latest status
   - Marks synced records as "Updated" in database

2. **Status Priority**: When multiple statuses exist, uses this hierarchy:
   - delivered > failed > accepted > sent

3. **Performance**: 
   - Processes 10 records concurrently
   - Only checks non-updated records
   - Efficient database queries

## Testing

Run the test script to verify everything is working:

```bash
python /workspace/appsail-python/test_zoho_sync.py
```

## API Endpoints

All endpoints require authentication:
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```

1. **Check Status**: `POST /zoho/status`
2. **Scheduler Status**: `POST /zoho/scheduler/status`
3. **Start Scheduler**: `POST /zoho/scheduler/start`
4. **Stop Scheduler**: `POST /zoho/scheduler/stop`
5. **Manual Sync**: `POST /zoho/sync`
6. **Test Queue Lookup**: `POST /zoho/test-queue-lookup`

## Deployment

1. Deploy the updated code to Zoho Catalyst
2. The scheduler will start automatically when the app starts
3. Monitor using the status endpoints
4. Check logs for sync activity

## Monitoring

Use the scheduler status endpoint to monitor:
- Is scheduler running?
- Last sync time
- Next sync time
- Total records synced
- Failed records count
- Sync duration

## Notes

- The "Updated" column in `delivered_logs` table prevents duplicate processing
- Access tokens are automatically refreshed every 55 minutes
- Failed updates are logged but don't stop the sync process
- Each sync is independent - failures don't affect future syncs

## Support

If you encounter issues:
1. Check scheduler status
2. Verify Zoho API credentials
3. Ensure database has "Updated" column
4. Check application logs for errors
5. Use test script to diagnose problems
# Zoho WhatsApp Status Synchronization Documentation

## Overview
This system automatically synchronizes WhatsApp message statuses from webhook data to Zoho Creator records every 60 minutes. It ensures that Zoho records are updated with the latest delivery status information collected through webhooks.

## Key Features

### 1. Automatic Token Management
- Access tokens are automatically refreshed every 55 minutes (5-minute buffer before expiration)
- No manual intervention required for token renewal

### 2. Efficient Processing
- Processes up to 1000 records per sync cycle
- Uses concurrent processing (10 records at a time) for faster updates
- Only processes records that haven't been updated yet (using the "Updated" flag)

### 3. Status Priority Hierarchy
The system follows this priority order when multiple statuses exist for the same message:
1. **delivered** (highest priority)
2. **failed**
3. **accepted**
4. **sent** (lowest priority)

### 4. Database Optimization
- Added "Updated" boolean column to `delivered_logs` table
- Only non-updated records are checked during sync
- Records are marked as updated after successful Zoho sync

## API Endpoints

### 1. Manual Sync Trigger
**POST** `/zoho/sync`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```
Starts a manual synchronization in the background.

### 2. Check Zoho Connection Status
**POST** `/zoho/status`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```
Returns current token status and pending records count.

### 3. Test Queue Lookup
**POST** `/zoho/test-queue-lookup`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#",
  "queue_id": "ab2661ac-2f7e-414b-a860-dba5c85763be"
}
```
Tests webhook data retrieval for a specific queue_id.

### 4. Scheduler Status
**POST** `/zoho/scheduler/status`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```
Returns scheduler status, last sync time, and statistics.

### 5. Start Scheduler
**POST** `/zoho/scheduler/start`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```
Manually starts the scheduler (normally starts automatically).

### 6. Stop Scheduler
**POST** `/zoho/scheduler/stop`
```json
{
  "username": "asingh50@deloitte.com",
  "password": "Abhi@1357#"
}
```
Stops the automatic synchronization.

## Synchronization Process

### Step 1: Token Generation
- Checks if current token is valid
- If expired or missing, generates new token using refresh token
- Token valid for 1 hour, refreshed after 55 minutes

### Step 2: Fetch Pending Records
- Queries Zoho for records where `Status != "delivered"`
- Retrieves up to 1000 records per sync
- Each record contains:
  - `ID` (Zoho record ID)
  - `Queue_ID_DV` (Queue ID to match with webhook data)
  - `Status`
  - `recipient_id`
  - Other metadata

### Step 3: Match with Webhook Data
- For each Zoho record, searches database for matching queue_id
- Looks in both `webhook_logs` and `delivered_logs` tables
- Only checks records where `Updated = false`
- Applies status priority to get the latest/highest priority status

### Step 4: Update Zoho Records
- Uses PATCH API to update each Zoho record with:
  - `Status`: Latest status from webhook
  - `Queue_ID_Webhook`: Queue ID from webhook
  - `Message_ID_Webhook`: WhatsApp message ID
  - `TimeStamp_Webhook`: Formatted timestamp
  - `recipient_id_Webhook`: Recipient phone number

### Step 5: Mark as Updated
- After successful Zoho update, marks the database record as `Updated = true`
- Prevents re-processing in future sync cycles

## Performance Optimizations

1. **Concurrent Processing**: Processes 10 records simultaneously
2. **Selective Querying**: Only fetches non-delivered and non-updated records
3. **Efficient Database Lookups**: Uses optimized queries when possible
4. **Automatic Scheduling**: Runs every 60 minutes without manual intervention
5. **Small Delays**: 0.1-second delay between updates to avoid API rate limits

## Error Handling

- Failed updates are logged but don't stop the sync process
- Network errors are caught and logged
- Token refresh failures trigger retry logic
- Each sync cycle is independent - failures don't affect future syncs

## Monitoring

Check sync status and statistics:
```python
# Response from /zoho/scheduler/status
{
  "is_running": true,
  "last_sync_time": "2025-01-30T10:30:00",
  "next_sync_time": "2025-01-30T11:30:00",
  "sync_interval_minutes": 60,
  "stats": {
    "total_synced": 450,
    "total_failed": 12,
    "last_sync_duration": 45.23
  }
}
```

## Database Schema

### delivered_logs table
- All existing columns plus:
- `Updated` (boolean): Indicates if record has been synced to Zoho

## Configuration

Current configuration in the code:
- Sync interval: 60 minutes
- Batch size: 10 concurrent updates
- Token refresh buffer: 5 minutes before expiration
- Max records per sync: 1000

## Deployment Notes

1. The scheduler starts automatically when the application starts
2. No cron job or external scheduler needed
3. Runs as a background thread in the Flask application
4. Survives application restarts (restarts automatically)

## Testing

1. Deploy the updated code
2. Check scheduler status: `POST /zoho/scheduler/status`
3. Monitor logs for sync activity
4. Verify Zoho records are being updated
5. Check that `Updated` flag is being set in database

## Troubleshooting

### Scheduler not running
- Check `/zoho/scheduler/status` endpoint
- Restart using `/zoho/scheduler/start`
- Check application logs for errors

### Records not updating
- Verify token is valid using `/zoho/status`
- Check if records have `Updated = false` in database
- Verify queue_id matches between Zoho and webhook data
- Check logs for specific error messages

### Performance issues
- Reduce batch size if API rate limits are hit
- Increase sync interval if needed
- Monitor sync duration in statistics
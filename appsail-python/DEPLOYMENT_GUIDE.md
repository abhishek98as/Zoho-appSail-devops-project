# Deployment Guide for Zoho Catalyst AppSail

## Prerequisites
- Access to Zoho Catalyst Console
- Project ID: 6751000000041001
- Environment: Development (ID: 60029031947)

## Files to Deploy

The following files have been updated/created and need to be deployed:

### Updated Files:
1. **main.py** - Main application with Zoho sync integration
   - Added scheduler initialization
   - Added new API endpoints for scheduler control
   - Integrated with zoho_sync_scheduler module

### New Files:
1. **zoho_sync_scheduler.py** - Automatic synchronization scheduler
2. **test_zoho_sync.py** - Test script for verification
3. **ZOHO_SYNC_DOCUMENTATION.md** - Detailed documentation
4. **ZOHO_SYNC_README.md** - Quick start guide

## Deployment Steps

### Option 1: Using Zoho Catalyst Web Console

1. **Login to Zoho Catalyst Console**
   - Go to https://catalyst.zoho.com/
   - Select project: tesst-knight (ID: 6751000000041001)

2. **Navigate to AppSail**
   - Click on "AppSail" in the left sidebar
   - Select your Python application

3. **Upload Updated Files**
   - Click on "Code Editor" or "File Manager"
   - Upload the following files to the appsail-python directory:
     - main.py (replace existing)
     - zoho_sync_scheduler.py (new file)
     - test_zoho_sync.py (optional, for testing)
     - Documentation files (optional)

4. **Deploy the Application**
   - Click "Deploy" button
   - Wait for deployment to complete

### Option 2: Using Catalyst CLI (Requires Authentication)

```bash
# 1. Login to Catalyst CLI
catalyst login

# 2. Navigate to project directory
cd /workspace

# 3. Deploy the application
catalyst deploy

# 4. Select the project and environment when prompted
```

### Option 3: Using Git Integration (If Configured)

```bash
# 1. Add all files
git add appsail-python/main.py appsail-python/zoho_sync_scheduler.py

# 2. Commit changes
git commit -m "Add Zoho synchronization scheduler"

# 3. Push to the connected repository
git push origin main
```

## Post-Deployment Verification

### 1. Check Application Status
Visit your application URL:
- Development: https://test-knight-50030314031.development.catalystappsail.in

### 2. Verify Scheduler is Running
```bash
curl -X POST https://test-knight-50030314031.development.catalystappsail.in/zoho/scheduler/status \
  -H "Content-Type: application/json" \
  -d '{
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
  }'
```

### 3. Check Zoho Connection
```bash
curl -X POST https://test-knight-50030314031.development.catalystappsail.in/zoho/status \
  -H "Content-Type: application/json" \
  -d '{
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
  }'
```

### 4. Run Test Script
```bash
# Update BASE_URL in test_zoho_sync.py to your deployment URL
python test_zoho_sync.py
```

## Expected Behavior After Deployment

1. **Automatic Start**: The scheduler will start automatically when the application starts
2. **First Sync**: Initial synchronization will begin immediately
3. **Recurring Sync**: Subsequent syncs will occur every 60 minutes
4. **Logging**: Check application logs for sync activity

## Monitoring

### Check Scheduler Status
The scheduler status endpoint will show:
```json
{
  "is_running": true,
  "last_sync_time": "2025-01-30T10:30:00",
  "next_sync_time": "2025-01-30T11:30:00",
  "sync_interval_minutes": 60,
  "stats": {
    "total_synced": 0,
    "total_failed": 0,
    "last_sync_duration": 0
  }
}
```

### Application Logs
Monitor logs in Catalyst Console:
1. Go to AppSail > Your App > Logs
2. Look for messages like:
   - "Zoho sync scheduler initialized and started"
   - "Starting scheduled Zoho synchronization..."
   - "Zoho synchronization completed: X updated, Y failed"

## Troubleshooting

### If Scheduler Doesn't Start
1. Check application logs for errors
2. Manually start using `/zoho/scheduler/start` endpoint
3. Verify database has "Updated" column in delivered_logs table

### If Records Aren't Updating
1. Check Zoho API credentials are correct
2. Verify access token is being generated
3. Check that webhook data exists for the queue IDs
4. Look for error messages in logs

### Performance Issues
1. Monitor sync duration in scheduler status
2. Check number of pending records
3. Verify database queries are efficient

## Important Notes

1. **Database Requirement**: Ensure the "Updated" boolean column exists in the delivered_logs table
2. **API Credentials**: The Zoho API credentials are hardcoded in the application
3. **Token Refresh**: Access tokens are automatically refreshed every 55 minutes
4. **Concurrent Processing**: The system processes 10 records at a time for efficiency

## Files Summary

```
appsail-python/
├── main.py                    # Updated main application
├── zoho_sync_scheduler.py     # New scheduler module
├── test_zoho_sync.py         # Test script
├── requirements.txt          # Dependencies (unchanged)
├── ZOHO_SYNC_DOCUMENTATION.md # Detailed docs
├── ZOHO_SYNC_README.md       # Quick start guide
└── DEPLOYMENT_GUIDE.md       # This file
```
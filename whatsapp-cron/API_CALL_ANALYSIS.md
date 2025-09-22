# API Call Frequency Analysis

## Overview

This document analyzes the API call frequency of the WhatsApp Status Sync Service over a 24-hour period.

## Configuration

- Sync interval: **10 minutes**
- Batch size: **100 records**
- Maximum batches per sync: **10 batches**
- Token refresh: Every **60 minutes** (with 5-minute buffer)

## API Call Types

### 1. Authentication API Calls

- **Endpoint**: `https://accounts.zoho.in/oauth/v2/token`
- **Method**: POST
- **Frequency**: Once every 55 minutes (60 minutes minus 5-minute buffer)
- **Calls per 24 hours**: 24 hours / 55 minutes = **26.18 calls** ≈ **27 calls**

### 2. Webhook API Calls

- **Endpoint**: `https://test-knight-50030314031.development.catalystappsail.in/webhook/master`
- **Method**: POST
- **Frequency**: 
  - Once per sync operation to pre-fetch all webhook data
  - Additional calls only if needed for specific queue IDs (rare)
- **Calls per 24 hours**: 24 hours / 10 minutes = **144 calls**

### 3. Zoho Creator API Calls (Fetch Records)

- **Endpoint**: `https://creator.zoho.in/api/v2.1/puarora_deloitte3/dashverify/report/WhatsApp_History_Form_Report`
- **Method**: GET
- **Frequency**: Up to 10 batches per sync operation (every 10 minutes)
- **Maximum calls per 24 hours**: (24 hours / 10 minutes) × 10 batches = **1,440 calls**
- **Realistic calls per 24 hours**: Typically much lower as batches stop when no more records are found
  - Estimated at 2-3 batches per sync = **288-432 calls**

### 4. Zoho Creator API Calls (Update Records)

- **Endpoint**: `https://creator.zoho.in/api/v2.1/puarora_deloitte3/dashverify/report/WhatsApp_History_Form_Report/{record_id}`
- **Method**: PATCH
- **Frequency**: One call per record that needs updating
- **Maximum calls per 24 hours**: (24 hours / 10 minutes) × 10 batches × 100 records = **14,400 calls**
- **Realistic calls per 24 hours**: Only records with matching queue IDs are updated
  - Estimated at 10-20% match rate = **1,440-2,880 calls**

## Total API Calls (24 Hours)

| API Type | Minimum | Maximum | Realistic Estimate |
|----------|---------|---------|-------------------|
| Authentication | 27 | 27 | 27 |
| Webhook Data | 144 | 144 | 144 |
| Zoho Creator (Fetch) | 144 | 1,440 | 288-432 |
| Zoho Creator (Update) | 0 | 14,400 | 1,440-2,880 |
| **TOTAL** | **315** | **16,011** | **1,899-3,483** |

## Optimization Strategies

1. **Batch Processing**
   - Already implemented - processes records in batches of 100
   - Limits the number of batches to 10 per sync operation

2. **Webhook Data Caching**
   - Pre-fetches all webhook data once per sync operation
   - Avoids multiple calls to the webhook API

3. **Sync Interval Adjustment**
   - Current interval: 10 minutes
   - Can be adjusted based on data volume and urgency
   - Increasing to 15 or 30 minutes would reduce API calls proportionally

4. **Token Management**
   - Reuses access token until near expiration
   - Avoids unnecessary authentication calls

5. **Early Termination**
   - Stops processing batches when no more records are found
   - Significantly reduces API calls when few records need updating

## Recommendations

1. **Monitor API Usage**
   - Track actual API call counts through the sync status endpoint
   - Adjust configuration if approaching rate limits

2. **Adjust Sync Interval**
   - Consider increasing the sync interval to 15 or 30 minutes if updates are not time-critical
   - This would reduce API calls by 33% or 66% respectively

3. **Optimize Batch Size**
   - The current batch size of 100 is a good balance
   - Increasing it would reduce fetch calls but increase the risk of timeouts

4. **Implement Incremental Sync**
   - Consider only fetching records updated since the last sync
   - This would significantly reduce API calls for fetch operations

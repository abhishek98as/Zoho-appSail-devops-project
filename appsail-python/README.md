# WhatsApp Webhook Handler with Catalyst NoSQL

This Flask application serves as a webhook handler for WhatsApp Business API messages via Meta's platform, using **Zoho Catalyst NoSQL** - a true document database for native JSON storage.

## Features

- ✅ **True NoSQL Document Storage** - Native JSON storage (eliminates data loss)
- ✅ **Document-based Collections** - Direct JSON document storage
- ✅ **Scalable for 1000+ Records Daily** - Catalyst's managed NoSQL infrastructure
- ✅ **Webhook Verification** - WhatsApp Business API compatible
- ✅ **Two NoSQL Collections**:
  - `webhook_logs`: Permanent storage (all sent/delivered messages)
  - `delivered_logs`: 24-hour retention (delivered messages only)
- ✅ **Advanced NoSQL Queries** - Query any field in JSON documents
- ✅ **Automatic 24-hour Cleanup** - Delivered logs auto-purge
- ✅ **Authenticated API Endpoints** - Secure data retrieval
- ✅ **Auto-scaling Collections** - Catalyst manages scaling automatically
- ✅ **Production Ready** - Built for Zoho Catalyst AppSail

## Endpoints

### Webhook Endpoints

- `GET /health` - Returns `ok` (health check)
- `GET /webhook?challange=123` - Verifies the webhook by responding with the challenge
- `POST /webhook` - Receives webhook events from WhatsApp and stores in Catalyst NoSQL

### API Endpoints (Authenticated)

- `POST /webhook/master` - Returns delivered messages from last 24 hours (delivered_logs collection)
- `POST /webhook/logs` - Returns all webhook data permanently stored (webhook_logs collection)
- `POST /webhook/query` - **NEW** Advanced NoSQL query with filters (collection, status, date, limit)
- `POST /webhook/cleanup` - **NEW** Manual cleanup of delivered logs

### Status & Monitoring

- `GET /webhook/status` - Returns application status and Catalyst NoSQL info
- `GET /webhook/all` - Legacy endpoint for backward compatibility

## Authentication

API endpoints require authentication using these credentials:

```json
{
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
}
```

Send credentials in the request body as JSON.

## Data Storage Architecture

### Catalyst NoSQL Collections

1. **webhook_logs** - Permanent document storage for all webhook data
   - Stores: All messages (sent + delivered) as JSON documents
   - Retention: Permanent (never deleted)
   - Purpose: Complete audit trail

2. **delivered_logs** - 24-hour document storage for delivered messages only
   - Stores: Only delivered status messages as JSON documents
   - Retention: 24 hours (auto-cleanup at midnight)
   - Purpose: Recent delivery tracking

### JSON Document Structure
Each document stores the complete webhook JSON natively, plus metadata fields for querying:

```json
{
  "_id": "auto_generated_document_id",
  "webhook_id": "wamid.HBgMOTE3MDY4NDgyNzQx...",
  "status": "delivered",
  "recipient_id": "917068482741",
  "timestamp": "1755263213",
  "phone_number_id": "408694838996380",
  "display_phone_number": "919154699658",
  "webhook_data": {
    "id": "374947405711015",
    "status": "delivered",
    "metadata": {
      "display_phone_number": "919154699658",
      "phone_number_id": "408694838996380"
    },
    "statuses": [
      {
        "id": "wamid.HBgMOTE3MDY4NDgyNzQx...",
        "timestamp": "1755263213",
        "recipient_id": "917068482741",
        "conversation": {
          "id": "a93ef6aeac37adf1c9870c5ae7b000b3",
          "timestamp": "12:34:56",
          "type": "utility"
        }
      }
    ]
  },
  "created_time": "2024-01-01T12:34:56Z",
  "date": "2024-01-01"
}
```

## Setup Instructions

### 1. NoSQL Collections Auto-Creation

✅ **No manual setup required!** Collections are automatically created when the first webhook is received.

### 2. Deploy Application

```bash
catalyst deploy appsail
```

The application will automatically use Catalyst NoSQL for document storage.

### 3. Test Setup

Check if NoSQL is working:

```bash
curl https://your-appsail-url/webhook/status
```

## Testing the API Endpoints

### Basic Data Retrieval

```bash
# Get delivered messages (last 24 hours)
curl -X POST https://your-appsail-url/webhook/master \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'

# Get all messages (permanent storage)
curl -X POST https://your-appsail-url/webhook/logs \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'
```

### Advanced NoSQL Query (NEW)

```bash
# Query with NoSQL filters
curl -X POST https://your-appsail-url/webhook/query \
  -H "Content-Type: application/json" \
  -d '{
    "username":"asingh50@deloitte.com",
    "password":"Abhi@1357#",
    "collection":"webhook_logs",
    "status":"delivered",
    "date":"2024-01-01",
    "limit":50
  }'
```

### Status Monitoring

```bash
# Check application and database status
curl https://your-appsail-url/webhook/status
```

## Benefits

✅ **True NoSQL Document Storage** - Native JSON storage (no conversion overhead)  
✅ **Unlimited Scalability** - Handles 1000+ records daily with auto-scaling  
✅ **Flexible Document Queries** - Query any field in JSON documents  
✅ **Schema Evolution** - Add fields without database migration  
✅ **Automatic 24-hour Cleanup** - Delivered logs self-manage storage  
✅ **Zero Configuration** - Collections auto-created on first webhook  
✅ **Production Ready** - Built on Catalyst's enterprise NoSQL infrastructure  

## Migration Benefits

✅ **From Local Files → Catalyst NoSQL**:
- **Eliminates data loss** from AppSail instance restarts
- **Native JSON storage** without conversion overhead  
- **Infinite scaling** for webhook data growth
- **Advanced document queries** on any JSON field
- **Managed infrastructure** with automatic backups
- **Global availability** with multi-region distribution

For detailed setup instructions, see [NOSQL_SETUP.md](NOSQL_SETUP.md)
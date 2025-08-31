# Catalyst NoSQL Setup for WhatsApp Webhook Handler

## 🎯 **Solution Overview**

This implementation uses **Zoho Catalyst NoSQL** - a true document database that natively stores JSON data. Perfect for WhatsApp webhook JSON storage with automatic scaling for 1000+ records daily.

## 📊 **NoSQL Collections Structure**

### Collection 1: webhook_logs (Permanent Storage)
Stores ALL webhook data (failed + sent + delivered) permanently as JSON documents.

**Document Structure:**
```json
{
  "_id": "auto_generated_id",
  "webhook_id": "message_id_from_whatsapp",
  "status": "failed|sent|delivered",
  "recipient_id": "phone_number",
  "web_timestamp": "unix_timestamp",
  "phone_number_id": "whatsapp_phone_id",
  "display_phone_number": "display_number",
  "webhook_data_json": "processed_webhook_data_as_json_string",
  "raw_webhook_data_json": "complete_original_webhook_response_as_json_string",
  "created_time": "2024-01-01T00:00:00Z",
  "web_date": "2024-01-01"
}
```

### Collection 2: delivered_logs (24-Hour Storage)
Stores ALL status types (failed, sent, delivered) with automatic 24-hour cleanup at midnight.

**Same document structure as webhook_logs**

**Key Updates:**
- Now stores **failed**, **sent**, and **delivered** statuses (not just delivered)
- Stores both **processed** and **complete raw webhook response**
- Automatic cleanup occurs exactly at **12:00 AM** daily
- Column names updated: `timestamp` → `web_timestamp`, `date` → `web_date`

## 🚀 **Setup Instructions**

### Step 1: Verify Prerequisites

1. **Catalyst Project**: Ensure you have a Catalyst project
2. **NoSQL Component**: NoSQL is enabled by default in Catalyst projects
3. **Python SDK**: Already included in `requirements.txt`

### Step 2: Deploy Application

The application will automatically create NoSQL collections on first webhook:

```bash
catalyst deploy appsail
```

### Step 3: Collections Auto-Creation

✅ **Collections are automatically created** when the first webhook is received
✅ **No manual setup required** in Catalyst Console
✅ **Schema-less design** - perfect for evolving webhook formats

### Step 4: Verify Setup

Check the status endpoint:
```bash
curl https://your-app-url/webhook/status
```

Expected response:
```json
{
  "app_status": "running",
  "storage_mode": "Catalyst NoSQL (Document Database)",
  "nosql_initialized": true,
  "nosql_collections": {
    "webhook_logs": "webhook_logs",
    "delivered_logs": "delivered_logs"
  },
  "features": {
    "persistent_nosql_storage": true,
    "document_based_json_storage": true,
    "auto_24h_cleanup_at_midnight": true,
    "stores_all_status_types": true,
    "stores_complete_webhook_response": true,
    "scalable_for_1000_plus_daily": true,
    "advanced_nosql_queries": true
  }
}
```

## 📡 **API Endpoints**

### 1. Webhook Data Reception
- **POST** `/webhook` - Receives WhatsApp webhook data
- Automatically stores in NoSQL collections based on status

### 2. Data Retrieval (Authenticated)

#### Get All Status Messages (24-hour) - NEW
```bash
curl -X POST https://your-app-url/webhook/master \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'
```
*Returns failed, sent, and delivered messages from last 24 hours*

#### Get Status-Specific Messages (24-hour) - NEW
```bash
# Get only failed messages
curl -X POST https://your-app-url/webhook/status/failed \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'

# Get only sent messages  
curl -X POST https://your-app-url/webhook/status/sent \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'

# Get only delivered messages
curl -X POST https://your-app-url/webhook/status/delivered \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'
```

#### Get All Messages (Permanent)
```bash
curl -X POST https://your-app-url/webhook/logs \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'
```
*Returns all messages permanently stored*

#### Advanced NoSQL Query (NEW)
```bash
curl -X POST https://your-app-url/webhook/query \
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

### 3. Management Endpoints

#### Status Check
```bash
curl https://your-app-url/webhook/status
```

#### Manual Cleanup (Authenticated)
```bash
curl -X POST https://your-app-url/webhook/cleanup \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'
```

## 📈 **Performance & Scale**

### For 1000+ Records Daily
- ✅ **Native JSON Storage** - No conversion overhead
- ✅ **Document-based Queries** - Query any field directly
- ✅ **Automatic Indexing** - Catalyst handles optimization
- ✅ **Horizontal Scaling** - Managed by Catalyst infrastructure
- ✅ **Schema Evolution** - Add fields without migration

### Data Retention Policy
- **webhook_logs**: ♾️ **Permanent storage** (all failed/sent/delivered records forever)
- **delivered_logs**: ⏰ **24-hour retention** (failed/sent/delivered - auto-cleanup at exactly 12:00 AM)

## 🔍 **NoSQL Query Capabilities**

### Simple Queries
```python
# Get all delivered messages
collection.get_documents_by_query({"status": "delivered"})

# Get messages from specific date
collection.get_documents_by_query({"date": "2024-01-01"})
```

### Advanced Queries
```python
# Complex criteria
query = {
    "status": "delivered",
    "date": {"$gte": "2024-01-01"},
    "recipient_id": "917068482741"
}
documents = collection.get_documents_by_query(query)
```

### Query Operators Supported
- `$eq` - Equal
- `$ne` - Not equal
- `$gt` - Greater than
- `$gte` - Greater than or equal
- `$lt` - Less than
- `$lte` - Less than or equal
- `$in` - In array
- `$nin` - Not in array

## 🔒 **Security Features**

- ✅ **Catalyst SDK Authentication** - Automatic token-based auth
- ✅ **API Endpoint Protection** - Username/password for data access
- ✅ **Encrypted Storage** - Catalyst handles encryption at rest
- ✅ **Access Control** - Managed through Catalyst Console
- ✅ **Document-level Security** - Fine-grained permissions

## 🚨 **Error Handling**

### Automatic Fallbacks
1. **SDK Initialization Failure** → Logged but app continues
2. **NoSQL Write Failure** → Logged with detailed error info
3. **Query Failure** → Returns empty array, logs error
4. **Collection Auto-Creation** → Happens on first document insert

### Monitoring
- **Application Logs** → All NoSQL operations logged
- **Catalyst Console** → Monitor collection usage and performance
- **Status Endpoint** → Real-time health check

## 🔄 **Migration Benefits**

### From Local Files → Catalyst NoSQL
1. ✅ **Eliminates Data Loss** - No more 5-minute instance restarts
2. ✅ **True Document Storage** - Native JSON without conversion
3. ✅ **Unlimited Scalability** - Handles millions of webhooks
4. ✅ **Flexible Queries** - Query any field in JSON
5. ✅ **Schema Evolution** - Add fields without downtime
6. ✅ **Managed Backups** - Catalyst handles backup/recovery
7. ✅ **Global Distribution** - Multi-region availability

## 🧪 **Testing Commands**

### 1. Test Webhook Reception
```bash
curl -X POST https://your-app-url/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [
      {
        "id": "374947405711015",
        "changes": [
          {
            "value": {
              "messaging_product": "whatsapp",
              "metadata": {
                "display_phone_number": "919154699658",
                "phone_number_id": "408694838996380"
              },
              "statuses": [
                {
                  "id": "test_message_id",
                  "status": "delivered",
                  "timestamp": "1640995200",
                  "recipient_id": "917068482741",
                  "conversation": {
                    "id": "test_conversation",
                    "origin": {"type": "utility"}
                  }
                }
              ]
            },
            "field": "messages"
          }
        ]
      }
    ]
  }'
```

### 2. Verify NoSQL Storage
```bash
curl https://your-app-url/webhook/status
# Check record_counts in response
```

### 3. Test NoSQL Queries
```bash
# Test delivered messages
curl -X POST https://your-app-url/webhook/master \
  -H "Content-Type: application/json" \
  -d '{"username":"asingh50@deloitte.com","password":"Abhi@1357#"}'

# Test advanced query
curl -X POST https://your-app-url/webhook/query \
  -H "Content-Type: application/json" \
  -d '{
    "username":"asingh50@deloitte.com",
    "password":"Abhi@1357#",
    "collection":"webhook_logs",
    "status":"delivered",
    "limit":10
  }'
```

## 💡 **NoSQL Best Practices**

### Document Design
- ✅ **Embed related data** - Store complete webhook JSON
- ✅ **Use consistent field names** - `webhook_id`, `status`, etc.
- ✅ **Add query-friendly fields** - `date`, `status` for filtering
- ✅ **Include metadata** - `created_time`, `phone_number_id`

### Query Optimization
- ✅ **Index frequently queried fields** - Catalyst auto-optimizes
- ✅ **Use specific queries** - Avoid broad scans
- ✅ **Implement pagination** - Use `limit` for large result sets
- ✅ **Cache common queries** - Reduce database load

## 🎉 **Result**

Your WhatsApp webhook handler now has:
- ✅ **True NoSQL Document Database** (no more data loss)
- ✅ **Native JSON Storage** (perfect for webhooks)
- ✅ **Unlimited Scalability** (handles 1000+ daily easily)
- ✅ **Flexible Query Engine** (query any JSON field)
- ✅ **Auto-scaling Collections** (managed by Catalyst)
- ✅ **24-hour Auto-cleanup** (delivered logs self-manage)
- ✅ **Production-ready Reliability** (enterprise infrastructure)

This completely solves the AppSail data persistence issue while providing enterprise-grade NoSQL database functionality! 🚀

## 🔗 **What Happens Next**

1. **Deploy**: Application auto-creates NoSQL collections
2. **Send Webhooks**: Data is stored as JSON documents
3. **Query Data**: Use powerful NoSQL queries to retrieve data
4. **Scale Automatically**: Catalyst handles all scaling needs
5. **Monitor**: Use status endpoint and Catalyst Console

Your webhook data is now stored permanently in a true NoSQL database that scales automatically! 🎯

from flask import Flask, request, jsonify, g
import json
import os
from datetime import datetime, timezone, time, timedelta
import functools
from werkzeug.security import check_password_hash, generate_password_hash

# Import Catalyst SDK - use the working import method
try:
    import zcatalyst_sdk
    # Let's try to find the correct classes in the SDK
    CATALYST_SDK_AVAILABLE = True
    IMPORT_METHOD = "zcatalyst_sdk"
    
    # Try to find CatalystApp class
    try:
        CatalystApp = zcatalyst_sdk.initialize
        NoSQLItem = None  # We'll figure this out
    except AttributeError:
        try:
            from zcatalyst_sdk.catalyst_app import CatalystApp
            NoSQLItem = None
        except ImportError:
            # Fallback - use the initialize method directly
            CatalystApp = None
            NoSQLItem = None
            
except ImportError as e:
    print(f"Catalyst SDK import failed: {e}")
    CATALYST_SDK_AVAILABLE = False
    CatalystApp = None
    NoSQLItem = None
    IMPORT_METHOD = "none"

app = Flask(__name__)

# Hardcoded credentials for API authentication
CREDENTIALS = {
    "username": "asingh50@deloitte.com",
    "password_hash": generate_password_hash("Abhi@1357#")
}

# NoSQL Table names with correct IDs
WEBHOOK_LOGS_TABLE = "webhook_logs"  # Table ID: 6751000000044786
DELIVERED_LOGS_TABLE = "delivered_logs"  # Table ID: 6751000000048519

# Catalyst Project Configuration
PROJECT_ID = "6751000000041001"

# Initialize Catalyst SDK
def get_catalyst_app():
    """Get Catalyst app instance"""
    if not CATALYST_SDK_AVAILABLE:
        print("Catalyst SDK not available")
        return None
    try:
        # Initialize using the correct zcatalyst_sdk method with request context
        catalyst_app = zcatalyst_sdk.initialize(req=request)
        return catalyst_app
    except Exception as e:
        print(f"Failed to initialize Catalyst app with request context: {e}")
        try:
            # Fallback: try without request context
            catalyst_app = zcatalyst_sdk.initialize()
            return catalyst_app
        except Exception as e2:
            print(f"Failed to initialize Catalyst app without context: {e2}")
            try:
                # Final attempt with manual project ID
                print(f"Attempting to initialize Catalyst with explicit project ID: {PROJECT_ID}")
                catalyst_app = zcatalyst_sdk.initialize(project_id=PROJECT_ID)
                print("Successfully initialized Catalyst with explicit project ID")
                return catalyst_app
            except Exception as e3:
                print(f"All Catalyst initialization methods failed: {e3}")
                return None

def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        try:
            auth_data = request.get_json(silent=True) or {}
        except Exception:
            auth_data = {}
            
        username = auth_data.get("username")
        password = auth_data.get("password")
        
        if not username or not password:
            return jsonify(error="Authentication required"), 401
            
        if username != CREDENTIALS["username"] or not check_password_hash(CREDENTIALS["password_hash"], password):
            return jsonify(error="Invalid credentials"), 401
            
        return f(*args, **kwargs)
    return decorated

def ensure_table_exists(catalyst_app, table_name):
    """Ensure table exists or create it with required columns"""
    try:
        datastore = catalyst_app.datastore()
        
        # Try to access the table
        try:
            table = datastore.table(table_name)
            # Test if table exists by trying to get columns
            columns = table.get_all_columns()
            print(f"Table '{table_name}' exists with columns: {[col.get_column_name() if hasattr(col, 'get_column_name') else str(col) for col in columns]}")
            return True
        except Exception as e:
            print(f"Table '{table_name}' might not exist: {e}")
            # For now, we'll assume the table needs to be created manually in Catalyst Console
            return False
            
    except Exception as e:
        print(f"Error checking table existence: {e}")
        return False

def store_webhook_data_nosql(webhook_data, table_name, raw_webhook_data=None):
    """Store webhook data in Catalyst Data Store with enhanced queue ID handling"""
    try:
        catalyst_app = get_catalyst_app()
        if not catalyst_app:
            print("Catalyst app not available, cannot store webhook data")
            return False
        
        # Ensure table exists (or log warning if it doesn't)
        if not ensure_table_exists(catalyst_app, table_name):
            print(f"Table '{table_name}' may not exist. Please create it in Catalyst Console.")
            
        # Prepare document for storage
        statuses = webhook_data.get("statuses", [{}])
        first_status = statuses[0] if statuses else {}
        metadata = webhook_data.get("metadata", {})
        
        # Check table schema and column support
        datastore = catalyst_app.datastore()
        table = datastore.table(table_name)
        
        try:
            columns = table.get_all_columns()
            column_names = []
            for col in columns:
                if hasattr(col, 'get_column_name'):
                    column_names.append(col.get_column_name())
                elif isinstance(col, dict):
                    column_names.append(col.get('column_name', str(col)))
                else:
                    column_names.append(str(col))
            
            supports_raw_data = 'raw_webhook_data_json' in column_names
            print(f"Table '{table_name}' columns: {column_names}")
            
        except Exception as col_error:
            print(f"Could not get columns for table '{table_name}': {col_error}")
            column_names = []
            supports_raw_data = False
        
        # Determine queue ID column (with fallback for missing column)
        queue_id_column = None
        queue_id_value = webhook_data.get("queue_id", "")
        
        if 'Queue_Id' in column_names:
            queue_id_column = 'Queue_Id'
        elif 'Queue_id' in column_names:
            queue_id_column = 'Queue_id'
        elif 'queue_id' in column_names:
            queue_id_column = 'queue_id'
        else:
            # Column doesn't exist - we'll store queue_id in JSON data only
            print(f"No queue_id column found in table '{table_name}'. Queue ID will be stored in JSON only.")
            queue_id_column = None
            
        # Extract timestamp for date field
        timestamp = first_status.get("timestamp")
        web_date = None
        if timestamp:
            try:
                dt = datetime.fromtimestamp(int(timestamp))
                web_date = dt.strftime("%Y-%m-%d")
            except:
                pass
                
        # Prepare record data - different structure for different tables
        if 'web_timestamp' in column_names:
            # webhook_logs table with full structure
            record_data = {
                'webhook_id': first_status.get("id", ""),
                'status': webhook_data.get("status", ""),
                'recipient_id': first_status.get("recipient_id", ""),
                'web_timestamp': first_status.get("timestamp", ""),
                'phone_number_id': metadata.get("phone_number_id", ""),
                'display_phone_number': metadata.get("display_phone_number", ""),
                'webhook_data_json': json.dumps(webhook_data),  # Store processed data as JSON string
                'created_time': datetime.now(timezone.utc).isoformat(),
                'web_date': web_date
            }
        else:
            # delivered_logs table with simplified structure
            record_data = {
                'webhook_id': first_status.get("id", ""),
                'status': webhook_data.get("status", ""),
                'recipient_id': first_status.get("recipient_id", ""),
                'webhook_data_json': json.dumps(webhook_data),  # Store processed data as JSON string
                'created_time': datetime.now(timezone.utc).isoformat()
            }
            
        # Only add queue_id column if it exists in the table schema
        if queue_id_column and queue_id_value:
            record_data[queue_id_column] = queue_id_value
        
        # Add raw webhook data only if table supports it
        if supports_raw_data and raw_webhook_data:
            try:
                record_data['raw_webhook_data_json'] = json.dumps(raw_webhook_data)
            except:
                pass
        
        # Use the correct insert_row method
        result = table.insert_row(record_data)
        print(f"Successfully stored webhook data in Data Store table '{table_name}'")
        
        return True
        
    except Exception as e:
        print(f"Error storing webhook data in Data Store: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def get_consolidated_webhook_data_nosql(table_name, status_filter=None):
    """Retrieve and consolidate webhook data by message ID, showing final status"""
    try:
        catalyst_app = get_catalyst_app()
        if not catalyst_app:
            return []
            
        datastore = catalyst_app.datastore()
        table = datastore.table(table_name)
        records = table.get_iterable_rows()
        
        # Group records by message ID
        message_groups = {}
        
        if records:
            for record in records:
                if hasattr(record, 'get'):
                    record_data = record
                elif hasattr(record, 'to_dict'):
                    record_data = record.to_dict()
                else:
                    record_data = record
                
                webhook_json_str = record_data.get("webhook_data_json", "{}")
                try:
                    webhook_json = json.loads(webhook_json_str)
                    statuses = webhook_json.get("statuses", [{}])
                    if statuses:
                        message_id = statuses[0].get("id", "")
                        queue_id = webhook_json.get("queue_id", record_data.get("Queue_Id", ""))
                        status = webhook_json.get("status", "")
                        recipient_id = statuses[0].get("recipient_id", "")
                        created_time = record_data.get("created_time", "")
                        
                        if message_id:
                            if message_id not in message_groups:
                                message_groups[message_id] = {
                                    "id": message_id,
                                    "queue_id": queue_id,
                                    "status": status,
                                    "recipient_id": recipient_id,
                                    "timestamp": created_time,
                                }
                            
                            # Update final status based on priority: failed > delivered > sent > accepted
                            current_status = message_groups[message_id]["status"]
                            if status == "failed" or (status == "delivered" and current_status not in ["failed"]) or \
                               (status == "sent" and current_status not in ["failed", "delivered"]) or \
                               (status == "accepted" and current_status == ""):
                                message_groups[message_id]["status"] = status
                                message_groups[message_id]["timestamp"] = created_time
                        
                except json.JSONDecodeError:
                    continue
        
        # Convert to list and apply status filter
        consolidated_data = []
        for message_data in message_groups.values():
            if status_filter and message_data["status"] != status_filter:
                continue
            
            final_data = {
                "id": message_data["id"],
                "queue_id": message_data["queue_id"],
                "status": message_data["status"],
                "recipient_id": message_data["recipient_id"],
                "timestamp": message_data["timestamp"]
            }
            consolidated_data.append(final_data)
        
        return consolidated_data
        
    except Exception as e:
        print(f"Error retrieving consolidated data from Data Store: {e}")
        return []

def process_webhook_data(data):
    """Process webhook data and return formatted entry for both standard and initial message formats"""
    try:
        # Check if this is an initial message format
        if "messaging_channel" in data and "message" in data and "response" in data:
            return process_initial_message_data(data)
        
        # Standard WhatsApp webhook format
        entry = data.get("entry", [{}])[0]
        value = entry.get("changes", [{}])[0].get("value", {})
        metadata = value.get("metadata", {})
        status_data = value.get("statuses", [{}])[0]
        
        timestamp = status_data.get("timestamp")
        if timestamp:
            dt = datetime.fromtimestamp(int(timestamp))
            formatted_time = dt.strftime("%H:%M:%S")
        else:
            formatted_time = "00:00:00"
        
        conversation = status_data.get("conversation", {})
        
        return {
            "id": entry.get("id"),
            "status": status_data.get("status"),
            "metadata": {
                "display_phone_number": metadata.get("display_phone_number"),
                "phone_number_id": metadata.get("phone_number_id")
            },
            "statuses": [
                {
                    "id": status_data.get("id"),
                    "timestamp": status_data.get("timestamp"),
                    "recipient_id": status_data.get("recipient_id"),
                    "conversation": {
                        "id": conversation.get("id"),
                        "timestamp": formatted_time,
                        "type": conversation.get("origin", {}).get("type")
                    }
                }
            ],
            "queue_id": None
        }
    except Exception as e:
        return {}

def process_initial_message_data(data):
    """Process initial message webhook data with accepted status"""
    try:
        message_data = data.get("message", {})
        response_data = data.get("response", {})
        
        queue_id = message_data.get("queue_id", "")
        messages = response_data.get("messages", [{}])
        first_message = messages[0] if messages else {}
        message_id = first_message.get("id", "")
        
        contacts = response_data.get("contacts", [{}])
        first_contact = contacts[0] if contacts else {}
        recipient_id = first_contact.get("wa_id", "")
        
        current_time = datetime.now().strftime("%H:%M:%S")
        current_timestamp = str(int(datetime.now().timestamp()))
        
        return {
            "id": queue_id,
            "status": "accepted",
            "metadata": {
                "display_phone_number": "",
                "phone_number_id": ""
            },
            "statuses": [
                {
                    "id": message_id,
                    "timestamp": current_timestamp,
                    "recipient_id": recipient_id,
                    "conversation": {
                        "id": queue_id,
                        "timestamp": current_time,
                        "type": "initial"
                    }
                }
            ],
            "queue_id": queue_id
        }
    except Exception as e:
        return {}

@app.route("/")
def index():
    return "WhatsApp Webhook Handler with Catalyst NoSQL", 200

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    challenge = (
        request.args.get("hub.challenge")
        or request.args.get("challenge")
        or request.args.get("challange")
    )
    if challenge:
        return challenge, 200
    return "ok", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        msgdata = request.get_json(force=True, silent=True) or {}
        print(f"Received webhook data: {json.dumps(msgdata)[:500]}...")
    except Exception as e:
        print(f"Failed to parse webhook JSON: {e}")
        msgdata = {}

    # Check webhook format - could be standard WhatsApp or initial message format
    is_standard_webhook = "object" in msgdata and msgdata.get("object") == "whatsapp_business_account"
    is_initial_message = "messaging_channel" in msgdata and "message" in msgdata and "response" in msgdata
    
    if not is_standard_webhook and not is_initial_message:
        print("Invalid webhook data format received")
        return jsonify(status="ok"), 200
    
    print("Valid webhook format detected, processing data")
    
    # Process the webhook data
    processed_data = process_webhook_data(msgdata)
    if not processed_data:
        print("Failed to process webhook data")
        return jsonify(status="ok"), 200
    
    status = processed_data.get("status", "")
    print(f"Processed webhook data: status={status}, id={processed_data.get('id')}")
    
    # Store in Catalyst NoSQL
    try:
        # Store all records in webhook_logs table (permanent storage) with raw data
        print(f"Storing data in {WEBHOOK_LOGS_TABLE}")
        store_result = store_webhook_data_nosql(processed_data, WEBHOOK_LOGS_TABLE, msgdata)
        if not store_result:
            print(f"Failed to store data in {WEBHOOK_LOGS_TABLE}")
        
        # Store all status types (accepted, failed, sent, delivered) in delivered_logs table (24-hour retention)
        if status in ["accepted", "failed", "sent", "delivered"]:
            print(f"Storing '{status}' data in {DELIVERED_LOGS_TABLE}")
            store_result = store_webhook_data_nosql(processed_data, DELIVERED_LOGS_TABLE, msgdata)
            if not store_result:
                print(f"Failed to store data in {DELIVERED_LOGS_TABLE}")
    except Exception as e:
        print(f"Exception during NoSQL storage operation: {e}")
        import traceback
        print(traceback.format_exc())

    return jsonify(status="ok"), 200

@app.route("/webhook/master", methods=["POST"])
@require_auth
def get_master_webhook():
    """Return consolidated webhook data (accepted, failed, sent, delivered) from last 24 hours"""
    try:
        data = get_consolidated_webhook_data_nosql(DELIVERED_LOGS_TABLE)
        return jsonify(data), 200
    except Exception as e:
        return jsonify(error="Failed to retrieve data"), 500

@app.route("/webhook/logs", methods=["POST"])
@require_auth
def get_master_logs():
    """Return all webhook data from permanent NoSQL storage"""
    try:
        data = get_consolidated_webhook_data_nosql(WEBHOOK_LOGS_TABLE)
        return jsonify(data), 200
    except Exception as e:
        return jsonify(error="Failed to retrieve data"), 500

@app.route("/webhook/status", methods=["GET"])
def get_status():
    """Return application status and NoSQL info"""
    catalyst_app = get_catalyst_app()
    catalyst_status = catalyst_app is not None
    
    status_info = {
        "app_status": "running",
        "storage_mode": "Catalyst NoSQL (Document Database)" if catalyst_status else "NoSQL not available",
        "catalyst_sdk_available": CATALYST_SDK_AVAILABLE,
        "catalyst_app_initialized": catalyst_status,
        "nosql_available": catalyst_status,
        "project_id": PROJECT_ID,
        "features": {
            "persistent_nosql_storage": catalyst_status,
            "stores_all_status_types": catalyst_status,
            "stores_complete_webhook_response": catalyst_status,
            "consolidated_message_tracking": catalyst_status,
            "queue_id_association": catalyst_status
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return jsonify(status_info), 200

if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For when running with gunicorn
    print("Flask app initialized for gunicorn")
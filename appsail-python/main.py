from flask import Flask, request, jsonify
import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta
import functools
from werkzeug.security import check_password_hash, generate_password_hash

# Import Catalyst SDK
try:
    import zcatalyst_sdk
    CATALYST_SDK_AVAILABLE = True
except ImportError as e:
    print(f"Catalyst SDK import failed: {e}")
    CATALYST_SDK_AVAILABLE = False

app = Flask(__name__)

# Hardcoded credentials for API authentication
CREDENTIALS = {
    "username": "asingh50@deloitte.com",
    "password_hash": generate_password_hash("Abhi@1357#")
}

# NoSQL Table names
WEBHOOK_LOGS_TABLE = "webhook_logs"
DELIVERED_LOGS_TABLE = "delivered_logs"

# Catalyst Project Configuration
PROJECT_ID = "6751000000041001"

# Initialize Catalyst SDK
def get_catalyst_app():
    """Get Catalyst app instance"""
    if not CATALYST_SDK_AVAILABLE:
        return None
    try:
        catalyst_app = zcatalyst_sdk.initialize(req=request)
        return catalyst_app
    except Exception as e:
        app.logger.error(f"Failed to initialize Catalyst app: {e}")
        try:
            catalyst_app = zcatalyst_sdk.initialize()
            return catalyst_app
        except Exception as e2:
            app.logger.error(f"Failed to initialize Catalyst app without context: {e2}")
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

def get_status_priority(status):
    """Get priority for status hierarchy: Delivered > failed > accepted > sent"""
    priority_map = {
        "delivered": 4,  # Highest priority
        "failed": 3,
        "accepted": 2,
        "sent": 1        # Lowest priority
    }
    return priority_map.get(status.lower(), 0)

def format_timestamp(timestamp_str):
    """Convert ISO timestamp to dd-MMM-yyyy HH:mm:ss format"""
    try:
        if not timestamp_str:
            return ""
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%d-%b-%Y %H:%M:%S")
    except Exception as e:
        app.logger.warning(f"Failed to format timestamp {timestamp_str}: {e}")
        return timestamp_str

def store_webhook_data_nosql(webhook_data, table_name, raw_webhook_data=None):
    """Store webhook data in Catalyst Data Store"""
    try:
        catalyst_app = get_catalyst_app()
        if not catalyst_app:
            app.logger.error("Catalyst app not available")
            return False
        
        datastore = catalyst_app.datastore()
        table = datastore.table(table_name)
        
        statuses = webhook_data.get("statuses", [{}])
        first_status = statuses[0] if statuses else {}
        metadata = webhook_data.get("metadata", {})
        
        # Determine queue ID column
        queue_id_column = None
        queue_id_value = webhook_data.get("queue_id", "")
        
        try:
            columns = table.get_all_columns()
            column_names = [col.get_column_name() if hasattr(col, 'get_column_name') else str(col) for col in columns]
            
            if 'Queue_Id' in column_names:
                queue_id_column = 'Queue_Id'
            elif 'Queue_id' in column_names:
                queue_id_column = 'Queue_id'
            elif 'queue_id' in column_names:
                queue_id_column = 'queue_id'
        except:
            pass
        
        # Prepare record data
        if 'web_timestamp' in column_names if 'column_names' in locals() else []:
            record_data = {
                'webhook_id': first_status.get("id", ""),
                'status': webhook_data.get("status", ""),
                'recipient_id': first_status.get("recipient_id", ""),
                'web_timestamp': first_status.get("timestamp", ""),
                'phone_number_id': metadata.get("phone_number_id", ""),
                'display_phone_number': metadata.get("display_phone_number", ""),
                'webhook_data_json': json.dumps(webhook_data),
                'created_time': datetime.now(timezone.utc).isoformat(),
                'web_date': datetime.now(timezone.utc).date().isoformat()
            }
        else:
            record_data = {
                'webhook_id': first_status.get("id", ""),
                'status': webhook_data.get("status", ""),
                'recipient_id': first_status.get("recipient_id", ""),
                'webhook_data_json': json.dumps(webhook_data),
                'created_time': datetime.now(timezone.utc).isoformat()
            }
        
        if queue_id_column and queue_id_value:
            record_data[queue_id_column] = queue_id_value
        
        result = table.insert_row(record_data)
        app.logger.info(f"Successfully stored webhook data in table '{table_name}'")
        return True
        
    except Exception as e:
        app.logger.error(f"Error storing webhook data: {e}")
        return False

def get_consolidated_webhook_data_nosql(table_name, status_filter=None):
    """Retrieve and consolidate webhook data showing LATEST status per queue_id/message_id"""
    try:
        catalyst_app = get_catalyst_app()
        if not catalyst_app:
            app.logger.error("Catalyst app not available")
            return []
            
        datastore = catalyst_app.datastore()
        table = datastore.table(table_name)
        records = table.get_iterable_rows()
        
        message_id_groups = {}
        
        for record in records:
            try:
                if hasattr(record, 'get'):
                    record_data = record
                elif hasattr(record, 'to_dict'):
                    record_data = record.to_dict()
                else:
                    record_data = record
                
                webhook_json_str = record_data.get("webhook_data_json", "{}")
                webhook_json = json.loads(webhook_json_str)
                
                statuses = webhook_json.get("statuses", [{}])
                if statuses:
                    message_id = statuses[0].get("id", "")
                    recipient_id = statuses[0].get("recipient_id", "")
                    queue_id = webhook_json.get("queue_id")
                    if not queue_id:
                        queue_id = record_data.get("Queue_Id", record_data.get("Queue_id", ""))
                    
                    status = webhook_json.get("status", "")
                    created_time = record_data.get("created_time", "")
                    whatsapp_event_timestamp = statuses[0].get("timestamp", "")
                    
                    processed_record = {
                        "message_id": message_id,
                        "queue_id": queue_id,
                        "status": status,
                        "recipient_id": recipient_id,
                        "timestamp": created_time,
                        "whatsapp_event_timestamp": whatsapp_event_timestamp,
                        "timestamp_obj": None,
                        "status_priority": get_status_priority(status)
                    }
                    
                    # Parse timestamp for sorting
                    try:
                        if whatsapp_event_timestamp:
                            whatsapp_ts = int(whatsapp_event_timestamp)
                            processed_record["timestamp_obj"] = datetime.fromtimestamp(whatsapp_ts)
                        else:
                            processed_record["timestamp_obj"] = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    except:
                        try:
                            processed_record["timestamp_obj"] = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                        except:
                            processed_record["timestamp_obj"] = datetime.min
                    
                    if message_id:
                        if message_id not in message_id_groups:
                            message_id_groups[message_id] = []
                        message_id_groups[message_id].append(processed_record)
                        
            except Exception as e:
                app.logger.warning(f"Failed to process record: {e}")
                continue
        
        # Process message_id groups - find latest status for each message_id
        consolidated_data = []
        
        for message_id, records in message_id_groups.items():
            if not records:
                continue
                
            # Sort by status hierarchy FIRST, then by WhatsApp timestamp
            latest_record = max(records, key=lambda r: (r["status_priority"], r["timestamp_obj"]))
            
            # Apply status filter if specified
            if status_filter and latest_record["status"] != status_filter:
                continue
            
            # Format the response
            final_data = {
                "id": latest_record["message_id"],
                "queue_id": latest_record["queue_id"],
                "status": latest_record["status"],
                "recipient_id": latest_record["recipient_id"],
                "timestamp": format_timestamp(latest_record["timestamp"])
            }
            consolidated_data.append(final_data)
        
        # Sort final results by timestamp (newest first)
        consolidated_data.sort(key=lambda x: x["timestamp"], reverse=True)
        
        app.logger.info(f"Retrieved {len(consolidated_data)} consolidated records from table '{table_name}'")
        return consolidated_data
        
    except Exception as e:
        app.logger.error(f"Error retrieving consolidated data: {e}")
        return []

def process_webhook_data(data):
    """Process webhook data and return formatted entry"""
    try:
        # Check if this is an initial message format
        if "messaging_channel" in data and "message" in data and "response" in data:
            return process_initial_message_data(data)
        
        # Standard WhatsApp webhook format
        entry = data.get("entry", [{}])[0]
        value = entry.get("changes", [{}])[0].get("value", {})
        metadata = value.get("metadata", {})
        status_data = value.get("statuses", [{}])[0]
        
        # Format timestamp
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
        app.logger.warning(f"Error processing webhook data: {e}")
        return {}

def process_initial_message_data(data):
    """Process initial message webhook data with accepted status"""
    try:
        message_data = data.get("message", {})
        response_data = data.get("response", {})
        
        queue_id = message_data.get("queue_id", "")
        message_id = response_data.get("messages", [{}])[0].get("id", "")
        recipient_id = response_data.get("contacts", [{}])[0].get("wa_id", "")
        
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
        app.logger.warning(f"Error processing initial message data: {e}")
        return {}

# Zoho API Integration Functions
class ZohoAPIManager:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None
        self.refresh_token = "1000.abe42f5ee32cbd2f51f4f2996c1a081b.49d7de9ca65bc657dac4d5dfaec9507c"
        self.client_id = "1000.09GO95AZNVR8RZ24MU799Y4HVFOIFP"
        self.client_secret = "24d22886c8d171fbb7210453bf3e2644ae4030bbf0"
        self.base_url = "https://creator.zoho.in/api/v2.1/puarora_deloitte3/dashverify/report/WhatsApp_History_Form_Report"
        
    def get_access_token(self):
        """Get or refresh Zoho access token"""
        current_time = datetime.now()
        
        # Check if token is still valid (with 5 minute buffer)
        if self.access_token and self.token_expiry and current_time < self.token_expiry:
            return self.access_token
            
        try:
            # Generate new access token
            token_url = "https://accounts.zoho.in/oauth/v2/token"
            params = {
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(token_url, params=params)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            # Set expiry to 55 minutes (5 minute buffer before 1 hour)
            self.token_expiry = current_time + timedelta(minutes=55)
            
            app.logger.info(f"Zoho access token refreshed, expires at {self.token_expiry}")
            return self.access_token
            
        except Exception as e:
            app.logger.error(f"Failed to get Zoho access token: {e}")
            return None
    
    def get_pending_records(self):
        """Get up to 1000 records that don't have delivered status"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return []
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            # Get records with status != "delivered"
            params = {
                "field_config": "custom",
                "fields": "Status,Queue_ID_DV,recipient_id,Initiated_Date_and_Time,DV_Reference",
                "max_records": 1000,
                "criteria": 'Status != "delivered"'
            }
            
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == 3000 and "data" in data:
                app.logger.info(f"Retrieved {len(data['data'])} pending records from Zoho")
                return data["data"]
            else:
                app.logger.warning(f"Unexpected Zoho response: {data}")
                return []
                
        except Exception as e:
            app.logger.error(f"Failed to get pending records from Zoho: {e}")
            return []
    
    def update_zoho_record(self, record_id, update_data):
        """Update a Zoho record with webhook data"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/{record_id}"
            payload = {"data": update_data}
            
            response = requests.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            
            app.logger.info(f"Successfully updated Zoho record {record_id}")
            return True
            
        except Exception as e:
            app.logger.error(f"Failed to update Zoho record {record_id}: {e}")
            return False

def get_latest_webhook_status_by_queue_id(queue_id):
    """Get the latest webhook status for a specific queue_id from database"""
    try:
        catalyst_app = get_catalyst_app()
        data_store = catalyst_app.datastore()
        
        # Search in both tables for the queue_id
        webhook_records = data_store.table(WEBHOOK_LOGS_TABLE).get_rows()
        delivered_records = data_store.table(DELIVERED_LOGS_TABLE).get_rows()
        
        all_records = []
        
        # Process webhook_logs table
        for record in webhook_records:
            record_data = record.get_row()
            webhook_json = json.loads(record_data.get("webhook_data_json", "{}"))
            
            if webhook_json.get("queue_id") == queue_id:
                status = webhook_json.get("status", "")
                message_id = webhook_json.get("id", "")
                recipient_id = ""
                
                # Extract recipient_id from statuses array
                statuses = webhook_json.get("statuses", [])
                if statuses:
                    recipient_id = statuses[0].get("recipient_id", "")
                
                created_time = record_data.get("created_time", "")
                
                all_records.append({
                    "status": status,
                    "message_id": message_id,
                    "queue_id": queue_id,
                    "recipient_id": recipient_id,
                    "timestamp": created_time,
                    "timestamp_obj": None,
                    "status_priority": get_status_priority(status)
                })
        
        # Process delivered_logs table
        for record in delivered_records:
            record_data = record.get_row()
            webhook_json = json.loads(record_data.get("webhook_data_json", "{}"))
            
            if webhook_json.get("queue_id") == queue_id:
                status = webhook_json.get("status", "")
                message_id = webhook_json.get("id", "")
                recipient_id = ""
                
                statuses = webhook_json.get("statuses", [])
                if statuses:
                    recipient_id = statuses[0].get("recipient_id", "")
                
                created_time = record_data.get("created_time", "")
                
                all_records.append({
                    "status": status,
                    "message_id": message_id,
                    "queue_id": queue_id,
                    "recipient_id": recipient_id,
                    "timestamp": created_time,
                    "timestamp_obj": None,
                    "status_priority": get_status_priority(status)
                })
        
        if not all_records:
            return None
        
        # Sort by status priority and timestamp to get the latest status
        latest_record = max(all_records, key=lambda r: (r["status_priority"], r["timestamp"]))
        
        # Parse timestamp for formatting
        try:
            timestamp_obj = datetime.fromisoformat(latest_record["timestamp"].replace('Z', '+00:00'))
            formatted_timestamp = timestamp_obj.strftime("%d-%b-%Y %H:%M:%S")
        except:
            formatted_timestamp = latest_record["timestamp"]
        
        return {
            "status": latest_record["status"],
            "message_id": latest_record["message_id"],
            "queue_id": latest_record["queue_id"],
            "recipient_id": latest_record["recipient_id"],
            "timestamp": formatted_timestamp
        }
        
    except Exception as e:
        app.logger.error(f"Error getting latest webhook status for queue_id {queue_id}: {e}")
        return None

def sync_zoho_with_webhooks():
    """Main function to sync Zoho records with latest webhook statuses"""
    try:
        app.logger.info("Starting Zoho-Webhook synchronization...")
        
        zoho_manager = ZohoAPIManager()
        
        # Get pending records from Zoho
        pending_records = zoho_manager.get_pending_records()
        if not pending_records:
            app.logger.info("No pending records found in Zoho")
            return
        
        app.logger.info(f"Processing {len(pending_records)} pending records...")
        
        updated_count = 0
        failed_count = 0
        
        for record in pending_records:
            try:
                zoho_queue_id = record.get("Queue_ID_DV")
                zoho_record_id = record.get("ID")
                zoho_status = record.get("Status")
                
                if not zoho_queue_id or not zoho_record_id:
                    app.logger.warning(f"Skipping record with missing data: {record}")
                    continue
                
                # Get latest webhook status from database
                webhook_data = get_latest_webhook_status_by_queue_id(zoho_queue_id)
                
                if webhook_data:
                    # Prepare update data for Zoho
                    update_data = {
                        "Status": webhook_data["status"],
                        "Queue_ID_Webhook": webhook_data["queue_id"],
                        "Message_ID_Webhook": webhook_data["message_id"],
                        "TimeStamp_Webhook": webhook_data["timestamp"],
                        "recipient_id_Webhook": webhook_data["recipient_id"]
                    }
                    
                    # Update Zoho record
                    if zoho_manager.update_zoho_record(zoho_record_id, update_data):
                        updated_count += 1
                        app.logger.info(f"Updated Zoho record {zoho_record_id} with status {webhook_data['status']}")
                    else:
                        failed_count += 1
                        app.logger.error(f"Failed to update Zoho record {zoho_record_id}")
                else:
                    app.logger.warning(f"No webhook data found for queue_id {zoho_queue_id}")
                    failed_count += 1
                
                # Small delay to avoid overwhelming Zoho API
                time.sleep(0.1)
                
            except Exception as e:
                app.logger.error(f"Error processing record {record}: {e}")
                failed_count += 1
        
        app.logger.info(f"Zoho synchronization completed: {updated_count} updated, {failed_count} failed")
        
    except Exception as e:
        app.logger.error(f"Error in Zoho-Webhook synchronization: {e}")

# Initialize Zoho manager
zoho_manager = ZohoAPIManager()

# Basic Routes
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
        app.logger.info(f"=== WEBHOOK RECEIVED ===")
        app.logger.info(f"Full webhook data: {json.dumps(msgdata, indent=2)}")
        
        # Check webhook format
        is_standard_webhook = "object" in msgdata and msgdata.get("object") == "whatsapp_business_account"
        is_initial_message = "messaging_channel" in msgdata and "message" in msgdata and "response" in msgdata
        
        if not is_standard_webhook and not is_initial_message:
            app.logger.warning(f"Unknown webhook format")
            return jsonify(status="ok"), 200
        
        # Process the webhook data
        processed_data = process_webhook_data(msgdata)
        if not processed_data:
            app.logger.warning("Failed to process webhook data")
            return jsonify(status="ok"), 200
        
        app.logger.info(f"Processed webhook data: {json.dumps(processed_data, indent=2)}")
        
        status = processed_data.get("status", "")
        
        # Store in Catalyst NoSQL
        try:
            # Store all records in webhook_logs table (permanent storage)
            stored_in_logs = store_webhook_data_nosql(processed_data, WEBHOOK_LOGS_TABLE, msgdata)
            if stored_in_logs:
                app.logger.info(f"Successfully stored data in NoSQL table '{WEBHOOK_LOGS_TABLE}'")
            else:
                app.logger.warning("Failed to store data in NoSQL webhook_logs table")
            
            # Store all status types in delivered_logs table
            if status in ["accepted", "failed", "sent", "delivered"]:
                stored_in_delivered = store_webhook_data_nosql(processed_data, DELIVERED_LOGS_TABLE, msgdata)
                if stored_in_delivered:
                    app.logger.info(f"Successfully stored {status} data in NoSQL table '{DELIVERED_LOGS_TABLE}'")
                else:
                    app.logger.warning(f"Failed to store {status} data in NoSQL table")
            else:
                app.logger.info(f"Skipping delivered storage - status is '{status}'")
                
        except Exception as e:
            app.logger.error(f"Exception during NoSQL storage operation: {e}")
        
        return jsonify(status="ok"), 200
        
    except Exception as e:
        app.logger.error(f"Error in webhook endpoint: {e}")
        return jsonify(status="error"), 500

@app.route("/webhook/master", methods=["POST"])
@require_auth
def get_master_webhook():
    """Return consolidated webhook data (accepted, failed, sent, delivered) from last 24 hours"""
    try:
        data = get_consolidated_webhook_data_nosql(DELIVERED_LOGS_TABLE)
        app.logger.info(f"Returning {len(data)} consolidated webhook records from NoSQL")
        return jsonify(data), 200
        
    except Exception as e:
        app.logger.error(f"Error retrieving master webhook data: {e}")
        return jsonify(error="Failed to retrieve data"), 500

@app.route("/webhook/status/<status_type>", methods=["POST"])
@require_auth
def get_status_specific_logs(status_type):
    """Return consolidated webhook data for specific final status"""
    try:
        valid_statuses = ["accepted", "failed", "sent", "delivered"]
        if status_type not in valid_statuses:
            return jsonify(error=f"Invalid status type. Valid options: {valid_statuses}"), 400
        
        data = get_consolidated_webhook_data_nosql(DELIVERED_LOGS_TABLE, status_filter=status_type)
        app.logger.info(f"Returning {len(data)} consolidated {status_type} webhook records from NoSQL")
        return jsonify(data), 200
        
    except Exception as e:
        app.logger.error(f"Error retrieving {status_type} webhook data: {e}")
        return jsonify(error="Failed to retrieve data"), 500

# Zoho Integration Routes
@app.route('/zoho/sync', methods=['POST'])
@require_auth
def zoho_sync_endpoint():
    """Manual endpoint to trigger Zoho-Webhook synchronization"""
    try:
        # Run synchronization in background
        import threading
        sync_thread = threading.Thread(target=sync_zoho_with_webhooks)
        sync_thread.start()
        
        return jsonify({
            "message": "Zoho synchronization started in background",
            "status": "started"
        })
        
    except Exception as e:
        app.logger.error(f"Error starting Zoho sync: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/zoho/status', methods=['POST'])
@require_auth
def zoho_status_endpoint():
    """Check Zoho API connection and token status"""
    try:
        # Test Zoho connection
        access_token = zoho_manager.get_access_token()
        if not access_token:
            return jsonify({
                "status": "error",
                "message": "Failed to get Zoho access token"
            })
        
        # Test getting pending records
        pending_records = zoho_manager.get_pending_records()
        
        return jsonify({
            "status": "success",
            "access_token": access_token[:20] + "..." if access_token else None,
            "token_expiry": zoho_manager.token_expiry.isoformat() if zoho_manager.token_expiry else None,
            "pending_records_count": len(pending_records) if pending_records else 0,
            "sample_pending_records": pending_records[:3] if pending_records else []
        })
        
    except Exception as e:
        app.logger.error(f"Error checking Zoho status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/zoho/test-queue-lookup', methods=['POST'])
@require_auth
def test_queue_lookup():
    """Test endpoint to look up webhook data for a specific queue_id"""
    try:
        data = request.get_json()
        queue_id = data.get('queue_id')
        
        if not queue_id:
            return jsonify({"error": "queue_id is required"}), 400
        
        # Look up webhook data
        webhook_data = get_latest_webhook_status_by_queue_id(queue_id)
        
        if webhook_data:
            return jsonify({
                "status": "success",
                "queue_id": queue_id,
                "webhook_data": webhook_data
            })
        else:
            return jsonify({
                "status": "not_found",
                "queue_id": queue_id,
                "message": "No webhook data found for this queue_id"
            })
        
    except Exception as e:
        app.logger.error(f"Error in test_queue_lookup: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    app.run(host="0.0.0.0", port=port, debug=False)

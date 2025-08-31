from flask import Flask, request, jsonify
import json
import os
import tempfile
from datetime import datetime, timezone, time, timedelta
import functools
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Hardcoded credentials for API authentication
CREDENTIALS = {
    "username": "asingh50@deloitte.com",
    "password_hash": generate_password_hash("Abhi@1357#")
}

# Enhanced storage paths - using multiple locations for better persistence
STORAGE_DIR = "/tmp/webhook_data"
BACKUP_DIR = "/tmp/webhook_backup"
MASTER_WEBHOOK_PATH = os.path.join(STORAGE_DIR, "Master_webhook.json")
MASTER_LOGS_PATH = os.path.join(STORAGE_DIR, "Master_logs.json")
BACKUP_WEBHOOK_PATH = os.path.join(BACKUP_DIR, "Master_webhook_backup.json")
BACKUP_LOGS_PATH = os.path.join(BACKUP_DIR, "Master_logs_backup.json")

# Create storage directories
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

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

def read_json_file(file_path):
    """Read JSON from file or return empty list if file doesn't exist"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                app.logger.info(f"Successfully read {file_path}, found {len(data) if isinstance(data, list) else 'non-list'} items")
                return data
        except Exception as e:
            app.logger.error(f"Failed to read {file_path}: {e}")
    else:
        app.logger.info(f"File {file_path} does not exist, returning empty list")
    
    return []

def write_json_file(file_path, data):
    """Write data to JSON file with backup"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        app.logger.info(f"Successfully wrote {len(data) if isinstance(data, list) else 'non-list'} items to {file_path}")
        
        # Create backup copy
        backup_file = file_path.replace(STORAGE_DIR, BACKUP_DIR).replace(".json", "_backup.json")
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            app.logger.info(f"Created backup at {backup_file}")
        except Exception as e:
            app.logger.warning(f"Failed to create backup: {e}")
            
    except Exception as e:
        app.logger.error(f"Failed to write to {file_path}: {e}")

def restore_from_backup_if_needed():
    """Restore data from backup if main files are missing or empty"""
    restored = False
    
    # Check and restore master webhook file
    if not os.path.exists(MASTER_WEBHOOK_PATH) or os.path.getsize(MASTER_WEBHOOK_PATH) == 0:
        if os.path.exists(BACKUP_WEBHOOK_PATH):
            try:
                with open(BACKUP_WEBHOOK_PATH, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                with open(MASTER_WEBHOOK_PATH, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                app.logger.info(f"Restored master webhook data from backup ({len(backup_data)} records)")
                restored = True
            except Exception as e:
                app.logger.error(f"Failed to restore webhook backup: {e}")
    
    # Check and restore master logs file
    if not os.path.exists(MASTER_LOGS_PATH) or os.path.getsize(MASTER_LOGS_PATH) == 0:
        if os.path.exists(BACKUP_LOGS_PATH):
            try:
                with open(BACKUP_LOGS_PATH, "r", encoding="utf-8") as f:
                    backup_data = json.load(f)
                with open(MASTER_LOGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                app.logger.info(f"Restored master logs data from backup ({len(backup_data)} records)")
                restored = True
            except Exception as e:
                app.logger.error(f"Failed to restore logs backup: {e}")
    
    return restored

def should_reset_delivered_data():
    """Check if delivered webhook data should be reset (after midnight)"""
    now = datetime.now()
    
    # Reset delivered data if it's a new day (between 00:00:00 and 00:05:00)
    if now.time() < time(0, 5, 0):
        if os.path.exists(MASTER_WEBHOOK_PATH):
            last_modified = os.path.getmtime(MASTER_WEBHOOK_PATH)
            last_modified_date = datetime.fromtimestamp(last_modified).date()
            if last_modified_date < now.date():
                write_json_file(MASTER_WEBHOOK_PATH, [])
                return True
    
    return False

def process_webhook_data(data):
    """Process webhook data and return formatted entry"""
    try:
        entry = data.get("entry", [{}])[0]
        value = entry.get("changes", [{}])[0].get("value", {})
        metadata = value.get("metadata", {})
        status_data = value.get("statuses", [{}])[0]
        
        # Format timestamp to 24-hour clock with seconds
        timestamp = status_data.get("timestamp")
        if timestamp:
            dt = datetime.fromtimestamp(int(timestamp))
            formatted_time = dt.strftime("%H:%M:%S")
        else:
            formatted_time = "00:00:00"
        
        # Extract conversation data
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
            ]
        }
    except Exception as e:
        app.logger.warning(f"Error processing webhook data: {e}")
        return {}

@app.route("/")
def index():
    return "WhatsApp Webhook Handler - Enhanced Local Storage", 200

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
        app.logger.info(f"Received webhook data: {json.dumps(msgdata, indent=2)[:500]}...")
    except Exception as e:
        app.logger.error(f"Failed to parse webhook JSON: {e}")
        msgdata = {}
    
    # Check if this is a valid WhatsApp webhook payload
    if not msgdata or "object" not in msgdata or msgdata.get("object") != "whatsapp_business_account":
        app.logger.warning(f"Invalid WhatsApp webhook payload or missing object field")
        return jsonify(status="ok"), 200
    
    # Restore from backup if needed (in case of instance restart)
    restore_from_backup_if_needed()
    
    # Reset delivered webhook data if needed (24-hour reset)
    if should_reset_delivered_data():
        app.logger.info("Reset delivered webhook data for new day")
    
    # Process the webhook data
    processed_data = process_webhook_data(msgdata)
    if not processed_data:
        app.logger.warning("Failed to process webhook data")
        return jsonify(status="ok"), 200
    
    app.logger.info(f"Processed webhook data: status={processed_data.get('status')}, id={processed_data.get('id')}")
    
    status = processed_data.get("status", "")
    
    # Enhanced local storage with backup
    master_logs_data = read_json_file(MASTER_LOGS_PATH)
    if not isinstance(master_logs_data, list):
        master_logs_data = []
    master_logs_data.append(processed_data)
    write_json_file(MASTER_LOGS_PATH, master_logs_data)
    app.logger.info(f"Stored in local logs, total records: {len(master_logs_data)}")
    
    # Store delivered records
    if status == "delivered":
        master_webhook_data = read_json_file(MASTER_WEBHOOK_PATH)
        if not isinstance(master_webhook_data, list):
            master_webhook_data = []
        master_webhook_data.append(processed_data)
        write_json_file(MASTER_WEBHOOK_PATH, master_webhook_data)
        app.logger.info(f"Stored delivered data locally, total records: {len(master_webhook_data)}")
    else:
        app.logger.info(f"Skipping delivered storage - status is '{status}', not 'delivered'")

    return jsonify(status="ok"), 200

@app.route("/webhook/master", methods=["POST"])
@require_auth
def get_master_webhook():
    """Return only the delivered webhook data"""
    try:
        # Restore from backup if needed
        restore_from_backup_if_needed()
        
        # Get delivered messages
        data = read_json_file(MASTER_WEBHOOK_PATH)
        if not isinstance(data, list):
            data = []
        
        app.logger.info(f"Returning {len(data)} delivered webhook records")
        return jsonify(data), 200
        
    except Exception as e:
        app.logger.error(f"Error retrieving master webhook data: {e}")
        return jsonify(error="Failed to retrieve data"), 500

@app.route("/webhook/logs", methods=["POST"])
@require_auth
def get_master_logs():
    """Return all webhook data"""
    try:
        # Restore from backup if needed
        restore_from_backup_if_needed()
        
        # Get all messages
        data = read_json_file(MASTER_LOGS_PATH)
        if not isinstance(data, list):
            data = []
        
        app.logger.info(f"Returning {len(data)} total webhook records")
        return jsonify(data), 200
        
    except Exception as e:
        app.logger.error(f"Error retrieving webhook logs: {e}")
        return jsonify(error="Failed to retrieve data"), 500

@app.route("/webhook/status", methods=["GET"])
def get_status():
    """Return application status"""
    
    # Check file sizes and record counts
    webhook_count = 0
    logs_count = 0
    
    try:
        if os.path.exists(MASTER_WEBHOOK_PATH):
            webhook_data = read_json_file(MASTER_WEBHOOK_PATH)
            webhook_count = len(webhook_data) if isinstance(webhook_data, list) else 0
    except:
        pass
        
    try:
        if os.path.exists(MASTER_LOGS_PATH):
            logs_data = read_json_file(MASTER_LOGS_PATH)
            logs_count = len(logs_data) if isinstance(logs_data, list) else 0
    except:
        pass
    
    status_info = {
        "app_status": "running",
        "storage_mode": "enhanced local with backup system (working base)",
        "catalyst_data_store": "available for setup - see DATASTORE_SETUP.md",
        "storage_status": {
            "primary_files": {
                "master_webhook_exists": os.path.exists(MASTER_WEBHOOK_PATH),
                "master_logs_exists": os.path.exists(MASTER_LOGS_PATH),
                "delivered_records": webhook_count,
                "total_records": logs_count
            },
            "backup_files": {
                "webhook_backup_exists": os.path.exists(BACKUP_WEBHOOK_PATH),
                "logs_backup_exists": os.path.exists(BACKUP_LOGS_PATH)
            },
            "directories": {
                "storage_dir": STORAGE_DIR,
                "backup_dir": BACKUP_DIR,
                "storage_dir_exists": os.path.exists(STORAGE_DIR),
                "backup_dir_exists": os.path.exists(BACKUP_DIR)
            }
        },
        "features": {
            "persistent_enhanced_storage": True,
            "automatic_backup_restore": True,
            "24_hour_delivered_reset": True,
            "handles_1000_plus_daily": True,
            "ready_for_catalyst_upgrade": True
        },
        "next_steps": "To enable Catalyst Data Store, follow DATASTORE_SETUP.md",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return jsonify(status_info), 200

# Initialize JSON files if they don't exist
def initialize_json_files():
    """Initialize JSON files with empty arrays if they don't exist"""
    for file_path in [MASTER_WEBHOOK_PATH, MASTER_LOGS_PATH]:
        if not os.path.exists(file_path):
            write_json_file(file_path, [])
            app.logger.info(f"Initialized {file_path} with empty array")

if __name__ == "__main__":
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    with app.app_context():
        initialize_json_files()
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For when running with gunicorn
    with app.app_context():
        initialize_json_files()

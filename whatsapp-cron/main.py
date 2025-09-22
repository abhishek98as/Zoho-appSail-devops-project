from flask import Flask, jsonify, request
import requests
import json
import os
import time
import threading
import logging
from datetime import datetime, timedelta
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
WEBHOOK_API_URL = "https://test-knight-50030314031.development.catalystappsail.in/webhook/master"
WEBHOOK_API_CREDENTIALS = {
    "username": "asingh50@deloitte.com",
    "password": "Abhi@1357#"
}

ZOHO_AUTH_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_AUTH_PARAMS = {
    "refresh_token": "1000.abe42f5ee32cbd2f51f4f2996c1a081b.49d7de9ca65bc657dac4d5dfaec9507c",
    "client_id": "1000.09GO95AZNVR8RZ24MU799Y4HVFOIFP",
    "client_secret": "24d22886c8d171fbb7210453bf3e2644ae4030bbf0",
    "grant_type": "refresh_token"
}

ZOHO_CREATOR_BASE_URL = "https://creator.zoho.in/api/v2.1/puarora_deloitte3/dashverify/report"
ZOHO_REPORT_NAME = "WhatsApp_History_Form_Report"

# Global variables
access_token = None
token_expiry = None
sync_in_progress = False
last_sync_time = None
sync_stats = {
    "total_records_fetched": 0,
    "records_updated": 0,
    "records_not_found": 0,
    "errors": 0,
    "last_run": None,
    "duration": 0
}

# Batch processing configuration
BATCH_SIZE = 100  # Number of records to process in one batch
SYNC_INTERVAL = 10 * 60  # 10 minutes in seconds

def get_access_token():
    """Get a valid Zoho access token"""
    global access_token, token_expiry
    
    current_time = datetime.now()
    
    # If token exists and is still valid, return it
    if access_token and token_expiry and current_time < token_expiry:
        logger.info("Using existing access token")
        return access_token
    
    # Otherwise, get a new token
    try:
        logger.info("Requesting new access token")
        response = requests.post(ZOHO_AUTH_URL, params=ZOHO_AUTH_PARAMS)
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)  # Default to 1 hour if not specified
        
        # Set expiry time (with a 5-minute buffer)
        token_expiry = current_time + timedelta(seconds=expires_in - 300)
        
        logger.info(f"New access token obtained, valid until {token_expiry}")
        return access_token
    
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None

# These functions have been replaced by inline code in the sync_data function
# for more efficient bulk processing

# This function has been replaced by inline code in the sync_data function
# for more efficient bulk processing

# This function has been replaced by the improved sync_data implementation
# that handles bulk processing more efficiently

def sync_data():
    """Sync data between webhook API and Zoho Creator"""
    global sync_in_progress, last_sync_time, sync_stats
    
    if sync_in_progress:
        logger.info("Sync already in progress, skipping")
        return
    
    sync_in_progress = True
    sync_start = time.time()
    
    try:
        logger.info("Starting data sync")
        
        # Reset stats for this run
        sync_stats = {
            "total_records_fetched": 0,
            "records_updated": 0,
            "records_not_found": 0,
            "errors": 0,
            "last_run": datetime.now().isoformat(),
            "duration": 0
        }
        
        # Get access token
        token = get_access_token()
        if not token:
            logger.error("Failed to get access token, aborting sync")
            sync_in_progress = False
            return
        
        logger.info("Successfully obtained access token")
        
        # STEP 1: Get all webhook data first (from Catalyst)
        logger.info("Fetching all webhook data from Catalyst")
        webhook_data = []
        webhook_map = {}  # Map of queue_id to webhook data
        
        try:
            response = requests.post(WEBHOOK_API_URL, json=WEBHOOK_API_CREDENTIALS)
            response.raise_for_status()
            webhook_data = response.json()
            logger.info(f"Fetched {len(webhook_data)} webhook records from Catalyst")
            
            # Create a map for quick lookup
            for entry in webhook_data:
                queue_id = entry.get("queue_id")
                if queue_id:
                    webhook_map[queue_id] = entry
            
            logger.info(f"Created map with {len(webhook_map)} unique queue IDs")
        except Exception as e:
            logger.error(f"Error fetching webhook data: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            sync_in_progress = False
            return
        
        if not webhook_data:
            logger.error("No webhook data available, aborting sync")
            sync_in_progress = False
            return
        
        # STEP 2: Get queued messages from Zoho Creator
        logger.info("Fetching queued messages from Zoho Creator")
        all_queued_messages = []
        batch_number = 1
        max_batches = 10  # Limit to 10 batches for safety
        
        while batch_number <= max_batches:
            try:
                logger.info(f"Fetching batch {batch_number} of queued messages")
                # Calculate offset based on batch number
                offset = (batch_number - 1) * BATCH_SIZE
                
                url = f"{ZOHO_CREATOR_BASE_URL}/{ZOHO_REPORT_NAME}"
                headers = {
                    "Authorization": f"Zoho-oauthtoken {token}",
                    "Content-Type": "application/json"
                }
                
                # Build the URL with query parameters manually to ensure proper formatting
                query_url = f"{url}?from={offset + 1}&limit={BATCH_SIZE}"
                query_url += "&criteria=(Status != \"delivered\" AND Status != \"failed\")"
                
                logger.info(f"Requesting URL: {query_url}")
                response = requests.get(query_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                batch_records = data.get("data", [])
                
                if not batch_records:
                    logger.info(f"No more records in batch {batch_number}, stopping fetch")
                    break
                
                logger.info(f"Fetched {len(batch_records)} records in batch {batch_number}")
                all_queued_messages.extend(batch_records)
                sync_stats["total_records_fetched"] += len(batch_records)
                
                batch_number += 1
                
                # Small delay between batches to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching batch {batch_number}: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Response: {e.response.text}")
                break
        
        logger.info(f"Total queued messages fetched: {len(all_queued_messages)}")
        
        if not all_queued_messages:
            logger.info("No queued messages to process, ending sync")
            sync_duration = time.time() - sync_start
            sync_stats["duration"] = sync_duration
            last_sync_time = datetime.now()
            sync_in_progress = False
            return
        
        # STEP 3: Match and prepare updates
        logger.info("Matching queued messages with webhook data")
        updates_needed = []
        
        for message in all_queued_messages:
            queue_id = message.get("Queue_ID_DV")
            record_id = message.get("ID")
            
            if not queue_id or not record_id:
                logger.warning(f"Missing Queue_ID_DV or ID in record: {message}")
                continue
            
            # Check if we have webhook data for this queue_id
            if queue_id in webhook_map:
                webhook_entry = webhook_map[queue_id]
                logger.info(f"Found matching webhook data for queue_id: {queue_id}")
                
                # Format timestamp for Zoho
                timestamp = webhook_entry.get("timestamp")
                formatted_timestamp = None
                if timestamp:
                    try:
                        # Parse the ISO format timestamp
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_timestamp = dt.strftime("%d-%b-%Y %H:%M:%S")
                    except Exception as e:
                        logger.warning(f"Could not parse timestamp {timestamp}: {str(e)}")
                        formatted_timestamp = timestamp
                
                # Prepare update data
                update_data = {
                    "record_id": record_id,
                    "data": {
                        "Status": webhook_entry.get("status", "unknown"),
                        "Queue_ID_Webhook": webhook_entry.get("queue_id", ""),
                        "Message_ID_Webhook": webhook_entry.get("id", ""),
                        "TimeStamp_Webhook": formatted_timestamp or "",
                        "recipient_id_Webhook": webhook_entry.get("recipient_id", "")
                    }
                }
                
                updates_needed.append(update_data)
            else:
                sync_stats["records_not_found"] += 1
                logger.info(f"No webhook data found for queue_id: {queue_id}")
        
        logger.info(f"Found {len(updates_needed)} records that need updating")
        
        # STEP 4: Process updates in batches
        if updates_needed:
            logger.info("Processing updates in batches")
            update_batch_size = 50  # Process 50 updates at a time
            
            for i in range(0, len(updates_needed), update_batch_size):
                batch = updates_needed[i:i + update_batch_size]
                logger.info(f"Processing update batch {i//update_batch_size + 1} with {len(batch)} records")
                
                # Process each update in the batch
                for update in batch:
                    try:
                        record_id = update["record_id"]
                        update_data = update["data"]
                        
                        url = f"{ZOHO_CREATOR_BASE_URL}/{ZOHO_REPORT_NAME}/{record_id}"
                        headers = {
                            "Authorization": f"Zoho-oauthtoken {token}",
                            "Content-Type": "application/json"
                        }
                        
                        payload = {"data": update_data}
                        
                        logger.info(f"Updating record {record_id} with status {update_data.get('Status')}")
                        response = requests.patch(url, headers=headers, json=payload)
                        response.raise_for_status()
                        
                        sync_stats["records_updated"] += 1
                        logger.info(f"Successfully updated record {record_id}")
                        
                    except Exception as e:
                        sync_stats["errors"] += 1
                        logger.error(f"Error updating record {update.get('record_id')}: {str(e)}")
                        if hasattr(e, 'response') and e.response:
                            logger.error(f"Response: {e.response.text}")
                
                # Check if token needs refresh between batches
                token = get_access_token()
                
                # Small delay between update batches
                if i + update_batch_size < len(updates_needed):
                    logger.info("Waiting 1 second before next update batch")
                    time.sleep(1)
        
        sync_duration = time.time() - sync_start
        sync_stats["duration"] = sync_duration
        
        logger.info(f"Sync completed in {sync_duration:.2f} seconds")
        logger.info(f"Stats: {json.dumps(sync_stats)}")
        
        last_sync_time = datetime.now()
    
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        logger.error(traceback.format_exc())
    
    finally:
        sync_in_progress = False

def start_scheduler():
    """Start the scheduler thread"""
    def run_scheduler():
        while True:
            try:
                sync_data()
            except Exception as e:
                logger.error(f"Error in scheduler: {str(e)}")
            
            # Sleep until next sync
            logger.info(f"Sleeping for {SYNC_INTERVAL} seconds until next sync")
            time.sleep(SYNC_INTERVAL)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler started")

# Routes
@app.route('/')
def index():
    return 'WhatsApp Status Sync Service is running!'

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "last_sync": last_sync_time.isoformat() if last_sync_time else None,
        "sync_in_progress": sync_in_progress
    })

@app.route('/sync/status')
def sync_status():
    return jsonify({
        "sync_in_progress": sync_in_progress,
        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
        "stats": sync_stats
    })

@app.route('/sync/trigger', methods=['POST'])
def trigger_sync():
    if sync_in_progress:
        return jsonify({"status": "error", "message": "Sync already in progress"}), 409
    
    # Start sync in a separate thread
    threading.Thread(target=sync_data).start()
    
    return jsonify({"status": "ok", "message": "Sync triggered"})

# Start the scheduler when the app starts
# Initialize scheduler
# Note: before_first_request is deprecated in newer Flask versions
# Using a different approach for initialization
with app.app_context():
    # This will run when the app is initialized by gunicorn
    if not sync_in_progress and not last_sync_time:
        threading.Thread(target=start_scheduler).start()

# For local development
if __name__ == '__main__':
    # Start the scheduler immediately when running locally
    start_scheduler()
    
    # Get the port from environment or use default
    port = int(os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "9000"))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For when running with gunicorn
    logger.info("Flask app initialized for gunicorn")

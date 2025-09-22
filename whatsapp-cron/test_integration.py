import requests
import json
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def get_access_token():
    """Get a valid Zoho access token"""
    try:
        logger.info("Requesting access token")
        response = requests.post(ZOHO_AUTH_URL, params=ZOHO_AUTH_PARAMS)
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get("access_token")
        
        logger.info(f"Access token obtained: {access_token[:10]}...")
        return access_token
    
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None

def get_webhook_data():
    """Get webhook data from the webhook API"""
    try:
        logger.info("Fetching webhook data")
        response = requests.post(WEBHOOK_API_URL, json=WEBHOOK_API_CREDENTIALS)
        response.raise_for_status()
        
        webhook_data = response.json()
        logger.info(f"Webhook data fetched: {len(webhook_data)} records")
        
        # Print sample data
        if webhook_data and len(webhook_data) > 0:
            logger.info(f"Sample webhook record: {json.dumps(webhook_data[0])}")
        
        return webhook_data
    
    except Exception as e:
        logger.error(f"Error getting webhook data: {str(e)}")
        return []

def get_queued_messages(token, max_records=10):
    """Get queued messages from Zoho Creator"""
    try:
        logger.info("Fetching queued messages from Zoho Creator")
        url = f"{ZOHO_CREATOR_BASE_URL}/{ZOHO_REPORT_NAME}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}"
        }
        
        # Simplified parameters - just get a few records without filtering
        params = {
            "max_records": max_records
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        records = data.get("data", [])
        logger.info(f"Zoho Creator records fetched: {len(records)} records")
        
        # Print sample data
        if records and len(records) > 0:
            logger.info(f"Sample Zoho record: {json.dumps(records[0])}")
        
        return records
    
    except Exception as e:
        logger.error(f"Error getting queued messages: {str(e)}")
        return []

def update_message_status(token, record_id, webhook_data):
    """Update message status in Zoho Creator"""
    try:
        logger.info(f"Updating message status for record {record_id}")
        url = f"{ZOHO_CREATOR_BASE_URL}/{ZOHO_REPORT_NAME}/{record_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json"
        }
        
        # Format timestamp for Zoho
        timestamp = webhook_data.get("timestamp")
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
            "data": {
                "Status": webhook_data.get("status", "unknown"),
                "Queue_ID_Webhook": webhook_data.get("queue_id", ""),
                "Message_ID_Webhook": webhook_data.get("id", ""),
                "TimeStamp_Webhook": formatted_timestamp or "",
                "recipient_id_Webhook": webhook_data.get("recipient_id", "")
            }
        }
        
        logger.info(f"Update payload: {json.dumps(update_data)}")
        
        response = requests.patch(url, headers=headers, json=update_data)
        response.raise_for_status()
        
        logger.info(f"Update successful for record {record_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating message status for record {record_id}: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response: {e.response.text}")
        return False

def test_integration():
    """Test the integration between webhook API and Zoho Creator"""
    # Get access token
    token = get_access_token()
    if not token:
        logger.error("Failed to get access token, aborting test")
        return
    
    # Get webhook data
    webhook_data = get_webhook_data()
    if not webhook_data:
        logger.error("Failed to get webhook data, aborting test")
        return
    
    # Get queued messages
    queued_messages = get_queued_messages(token)
    if not queued_messages:
        logger.warning("No queued messages found in Zoho Creator")
        return
    
    # Create a map of queue_id to webhook data
    webhook_map = {}
    for entry in webhook_data:
        queue_id = entry.get("queue_id")
        if queue_id:
            webhook_map[queue_id] = entry
    
    logger.info(f"Found {len(webhook_map)} unique queue IDs in webhook data")
    
    # Match and update
    matches_found = 0
    updates_successful = 0
    
    for message in queued_messages:
        queue_id = message.get("Queue_ID_DV")
        record_id = message.get("ID")
        
        if not queue_id or not record_id:
            logger.warning(f"Missing Queue_ID_DV or ID in record: {message}")
            continue
        
        # Check if we have webhook data for this queue_id
        if queue_id in webhook_map:
            matches_found += 1
            logger.info(f"Match found for queue_id {queue_id}")
            
            # Update message status
            success = update_message_status(token, record_id, webhook_map[queue_id])
            if success:
                updates_successful += 1
    
    logger.info(f"Integration test completed:")
    logger.info(f"- Total webhook records: {len(webhook_data)}")
    logger.info(f"- Total queued messages: {len(queued_messages)}")
    logger.info(f"- Matches found: {matches_found}")
    logger.info(f"- Updates successful: {updates_successful}")

if __name__ == "__main__":
    logger.info("Starting integration test")
    test_integration()
    logger.info("Integration test completed")

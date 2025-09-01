"""
Zoho Sync Scheduler - Handles automatic synchronization between Zoho and webhook data
"""
import threading
import time
import logging
from datetime import datetime, timedelta
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import Catalyst SDK
try:
    import zcatalyst_sdk
    CATALYST_SDK_AVAILABLE = True
except ImportError:
    CATALYST_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

class ZohoSyncScheduler:
    def __init__(self, app, zoho_manager, catalyst_app=None):
        self.app = app
        self.zoho_manager = zoho_manager
        self.catalyst_app = catalyst_app
        self.sync_interval = 3600  # 60 minutes in seconds
        self.is_running = False
        self.sync_thread = None
        self.last_sync_time = None
        self.sync_stats = {
            "total_synced": 0,
            "total_failed": 0,
            "last_sync_duration": 0
        }
        
    def start(self):
        """Start the scheduled sync process"""
        if self.is_running:
            logger.warning("Sync scheduler is already running")
            return
            
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
        logger.info("Zoho sync scheduler started")
        
    def stop(self):
        """Stop the scheduled sync process"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("Zoho sync scheduler stopped")
        
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.is_running:
            try:
                # Run sync immediately on start, then wait for interval
                self._perform_sync()
                
                # Wait for the next sync interval
                time.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error in sync scheduler: {e}")
                # Wait a bit before retrying
                time.sleep(60)
                
    def _perform_sync(self):
        """Perform the actual synchronization"""
        start_time = time.time()
        logger.info("Starting scheduled Zoho synchronization...")
        
        try:
            # Get pending records from Zoho
            pending_records = self.zoho_manager.get_pending_records()
            if not pending_records:
                logger.info("No pending records found in Zoho")
                return
                
            logger.info(f"Processing {len(pending_records)} pending records...")
            
            # Process records in batches for efficiency
            batch_size = 10  # Process 10 records concurrently
            updated_count = 0
            failed_count = 0
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Submit all tasks
                future_to_record = {
                    executor.submit(self._process_single_record, record): record 
                    for record in pending_records
                }
                
                # Process completed tasks
                for future in as_completed(future_to_record):
                    record = future_to_record[future]
                    try:
                        success, record_id = future.result()
                        if success:
                            updated_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Error processing record {record}: {e}")
                        failed_count += 1
                        
            # Update statistics
            self.sync_stats["total_synced"] += updated_count
            self.sync_stats["total_failed"] += failed_count
            self.sync_stats["last_sync_duration"] = time.time() - start_time
            self.last_sync_time = datetime.now()
            
            logger.info(f"Zoho synchronization completed: {updated_count} updated, {failed_count} failed")
            logger.info(f"Sync duration: {self.sync_stats['last_sync_duration']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
            
    def _process_single_record(self, record):
        """Process a single Zoho record"""
        try:
            zoho_queue_id = record.get("Queue_ID_DV")
            zoho_record_id = record.get("ID")
            
            if not zoho_queue_id or not zoho_record_id:
                logger.warning(f"Skipping record with missing data: {record}")
                return False, None
                
            # Get latest webhook status from database
            webhook_data = self._get_latest_webhook_status_optimized(zoho_queue_id)
            
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
                if self.zoho_manager.update_zoho_record(zoho_record_id, update_data):
                    # Mark the record as updated in the database
                    self._mark_record_as_updated(webhook_data.get("record_id"))
                    logger.info(f"Updated Zoho record {zoho_record_id} with status {webhook_data['status']}")
                    return True, zoho_record_id
                else:
                    logger.error(f"Failed to update Zoho record {zoho_record_id}")
                    return False, zoho_record_id
            else:
                logger.warning(f"No webhook data found for queue_id {zoho_queue_id}")
                return False, zoho_record_id
                
        except Exception as e:
            logger.error(f"Error processing record {record}: {e}")
            return False, None
            
    def _get_latest_webhook_status_optimized(self, queue_id):
        """Get the latest webhook status for a specific queue_id (optimized version)"""
        try:
            if not self.catalyst_app:
                self.catalyst_app = zcatalyst_sdk.initialize()
                
            data_store = self.catalyst_app.datastore()
            
            # Query only non-updated records from delivered_logs table
            delivered_table = data_store.table("delivered_logs")
            
            # Use ZCQL query for better performance
            query = f"SELECT ROWID, webhook_data_json, created_time FROM delivered_logs WHERE queue_id = '{queue_id}' AND Updated = false"
            
            try:
                results = data_store.execute_zcql_query(query)
            except:
                # Fallback to row-based search if ZCQL is not available
                results = []
                all_rows = delivered_table.get_rows()
                for row in all_rows:
                    row_data = row.get_row()
                    if not row_data.get("Updated", False):
                        webhook_json = json.loads(row_data.get("webhook_data_json", "{}"))
                        if webhook_json.get("queue_id") == queue_id:
                            results.append(row_data)
            
            # Also check webhook_logs table
            webhook_table = data_store.table("webhook_logs")
            webhook_rows = webhook_table.get_rows()
            
            all_records = []
            
            # Process delivered_logs records
            for record in results:
                if isinstance(record, dict):
                    row_data = record
                else:
                    row_data = record.get_row() if hasattr(record, 'get_row') else record
                    
                webhook_json = json.loads(row_data.get("webhook_data_json", "{}"))
                
                status = webhook_json.get("status", "")
                message_id = webhook_json.get("id", "")
                recipient_id = ""
                
                statuses = webhook_json.get("statuses", [])
                if statuses:
                    recipient_id = statuses[0].get("recipient_id", "")
                    
                created_time = row_data.get("created_time", "")
                
                all_records.append({
                    "status": status,
                    "message_id": message_id,
                    "queue_id": queue_id,
                    "recipient_id": recipient_id,
                    "timestamp": created_time,
                    "timestamp_obj": None,
                    "status_priority": self._get_status_priority(status),
                    "record_id": row_data.get("ROWID")
                })
                
            # Process webhook_logs records
            for row in webhook_rows:
                row_data = row.get_row()
                webhook_json = json.loads(row_data.get("webhook_data_json", "{}"))
                
                if webhook_json.get("queue_id") == queue_id:
                    status = webhook_json.get("status", "")
                    message_id = webhook_json.get("id", "")
                    recipient_id = ""
                    
                    statuses = webhook_json.get("statuses", [])
                    if statuses:
                        recipient_id = statuses[0].get("recipient_id", "")
                        
                    created_time = row_data.get("created_time", "")
                    
                    all_records.append({
                        "status": status,
                        "message_id": message_id,
                        "queue_id": queue_id,
                        "recipient_id": recipient_id,
                        "timestamp": created_time,
                        "timestamp_obj": None,
                        "status_priority": self._get_status_priority(status),
                        "record_id": None  # webhook_logs doesn't need updating
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
                "timestamp": formatted_timestamp,
                "record_id": latest_record.get("record_id")
            }
            
        except Exception as e:
            logger.error(f"Error getting latest webhook status for queue_id {queue_id}: {e}")
            return None
            
    def _mark_record_as_updated(self, record_id):
        """Mark a record as updated in the delivered_logs table"""
        if not record_id:
            return
            
        try:
            if not self.catalyst_app:
                self.catalyst_app = zcatalyst_sdk.initialize()
                
            data_store = self.catalyst_app.datastore()
            table = data_store.table("delivered_logs")
            
            # Update the record
            update_data = {"Updated": True}
            table.update_row(record_id, update_data)
            
            logger.debug(f"Marked record {record_id} as updated")
            
        except Exception as e:
            logger.error(f"Error marking record {record_id} as updated: {e}")
            
    def _get_status_priority(self, status):
        """Get priority for status hierarchy"""
        priority_map = {
            "delivered": 4,
            "failed": 3,
            "accepted": 2,
            "sent": 1
        }
        return priority_map.get(status.lower(), 0)
        
    def get_status(self):
        """Get the current status of the scheduler"""
        return {
            "is_running": self.is_running,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "next_sync_time": (self.last_sync_time + timedelta(seconds=self.sync_interval)).isoformat() if self.last_sync_time else None,
            "sync_interval_minutes": self.sync_interval / 60,
            "stats": self.sync_stats
        }
"""
Redis Pub/Sub Alert System
===========================

This module handles Redis pub/sub for critical contradiction alerts.
"""

import redis
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from celery_config import REDIS_HOST, REDIS_PORT, REDIS_DB, ALERTS_CHANNEL


class RedisAlertManager:
    """
    Manages Redis pub/sub for critical contradiction alerts.
    """
    
    def __init__(self):
        self.redis_client = redis.StrictRedis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB,
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        self.alert_handlers: Dict[str, Callable] = {}
        self.is_listening = False
    
    def add_alert_handler(self, handler_name: str, handler_func: Callable):
        """
        Add a handler function for processing alerts.
        
        Args:
            handler_name: Name of the handler
            handler_func: Function to handle alerts
        """
        self.alert_handlers[handler_name] = handler_func
    
    def remove_alert_handler(self, handler_name: str):
        """
        Remove an alert handler.
        
        Args:
            handler_name: Name of the handler to remove
        """
        if handler_name in self.alert_handlers:
            del self.alert_handlers[handler_name]
    
    def publish_alert(self, alert_data: Dict[str, Any]):
        """
        Publish an alert to the alerts channel.
        
        Args:
            alert_data: Dictionary containing alert information
        """
        try:
            alert_message = {
                **alert_data,
                "timestamp": datetime.utcnow().isoformat(),
                "alert_type": "contradiction_detected"
            }
            
            message = json.dumps(alert_message)
            self.redis_client.publish(ALERTS_CHANNEL, message)
            print(f"Published alert: {alert_message}")
            
        except Exception as e:
            print(f"Error publishing alert: {str(e)}")
    
    async def start_listening(self):
        """
        Start listening for alerts on the alerts channel.
        """
        if self.is_listening:
            print("Already listening for alerts")
            return
        
        self.pubsub.subscribe(ALERTS_CHANNEL)
        self.is_listening = True
        print(f"Started listening for alerts on channel: {ALERTS_CHANNEL}")
        
        # Process messages in a separate task
        asyncio.create_task(self._process_messages())
    
    async def stop_listening(self):
        """
        Stop listening for alerts.
        """
        if not self.is_listening:
            return
        
        self.pubsub.unsubscribe(ALERTS_CHANNEL)
        self.is_listening = False
        print("Stopped listening for alerts")
    
    async def _process_messages(self):
        """
        Process incoming alert messages.
        """
        while self.is_listening:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    await self._handle_message(message)
                    
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Dict[str, Any]):
        """
        Handle a single alert message.
        
        Args:
            message: Redis message containing alert data
        """
        try:
            alert_data = json.loads(message['data'])
            print(f"Received alert: {alert_data}")
            
            # Execute all registered handlers
            for handler_name, handler_func in self.alert_handlers.items():
                try:
                    if asyncio.iscoroutinefunction(handler_func):
                        await handler_func(alert_data)
                    else:
                        handler_func(alert_data)
                except Exception as e:
                    print(f"Error in handler {handler_name}: {str(e)}")
                    
        except Exception as e:
            print(f"Error handling alert message: {str(e)}")
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the alert system.
        
        Returns:
            Dictionary containing alert system statistics
        """
        return {
            "is_listening": self.is_listening,
            "channel": ALERTS_CHANNEL,
            "handlers_registered": len(self.alert_handlers),
            "handler_names": list(self.alert_handlers.keys()),
            "redis_connected": self.redis_client.ping()
        }


# Default alert handlers
async def log_critical_contradiction(alert_data: Dict[str, Any]):
    """
    Default handler that logs critical contradictions.
    """
    print(f"CRITICAL CONTRADICTION DETECTED:")
    print(f"  Story: {alert_data.get('story_id')}")
    print(f"  From: {alert_data.get('from')}")
    print(f"  To: {alert_data.get('to')}")
    print(f"  Severity: {alert_data.get('severity')}")
    print(f"  Reason: {alert_data.get('reason')}")
    print(f"  Time: {alert_data.get('detected_at')}")


def store_alert_in_database(alert_data: Dict[str, Any]):
    """
    Handler that stores alerts in a database (placeholder).
    """
    # TODO: Implement database storage
    pass


def send_notification(alert_data: Dict[str, Any]):
    """
    Handler that sends notifications (placeholder).
    """
    # TODO: Implement email/webhook notifications
    pass


# Global alert manager instance
alert_manager = RedisAlertManager()

# Register default handlers
alert_manager.add_alert_handler("log_critical", log_critical_contradiction)
alert_manager.add_alert_handler("store_database", store_alert_in_database)
alert_manager.add_alert_handler("send_notification", send_notification)

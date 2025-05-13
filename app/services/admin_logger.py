"""
Admin Logger Service

This module provides logging functionality specifically for admin-related activities.
In production environments like Heroku, it logs to stdout/stderr.
In development environments, it can also log to files for debugging.
"""

import logging
import os
import sys
from datetime import datetime
import json
from typing import Dict, Any, Optional, List

class AdminLogger:
    """
    Admin Logger class to handle specialized logging for admin operations
    """
    
    def __init__(self):
        """
        Initialize the AdminLogger.
        Creates a base logger and prepares the log directory if in development.
        """
        # Environment check - determine if we're on Heroku/production
        self.is_production = os.environ.get('ENVIRONMENT', 'development') == 'production'
        
        # Set up the base logger
        self.logger = logging.getLogger("admin_logger")
        self.logger.setLevel(logging.INFO)
        
        # Create a base formatter
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set up log directory only in development mode
        self.in_memory_logs = []  # Store recent logs in memory for production
        
        if not self.is_production:
            try:
                # Create main log directory for today
                today = datetime.now().strftime('%Y-%m-%d')
                self.log_dir = f"logs/admin/{today}"
                os.makedirs(self.log_dir, exist_ok=True)
            except Exception as e:
                self.logger.warning(f"Could not create log directory: {e}")
                self.log_dir = None
        else:
            self.log_dir = None
    
    def _get_logger(self, operation: str) -> logging.Logger:
        """
        Get a logger for a specific operation.
        In development, creates a file handler.
        In production, logs to stdout and keeps in memory.
        
        Args:
            operation: Name of the operation (e.g., 'login', 'user_management')
            
        Returns:
            logging.Logger: Logger for the specified operation
        """
        # Create a new logger for this operation
        logger = logging.getLogger(f"admin_logger.{operation}")
        
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # Create timestamp
        timestamp = datetime.now().strftime('%H%M%S')
        
        # In production (Heroku), use StreamHandler to log to stdout
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(self.formatter)
        logger.addHandler(stream_handler)
        
        # In development, also add a file handler if possible
        if not self.is_production and self.log_dir:
            try:
                log_file = f"{self.log_dir}/{operation}_{timestamp}.log"
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(self.formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # Just use stdout if file logging fails
                logger.warning(f"Could not set up file logging: {e}")
        
        return logger
    
    def log_user_activity(self, admin_id: int, action: str, user_id: int, details: Optional[Dict[str, Any]] = None):
        """
        Log user management activities performed by admins
        
        Args:
            admin_id: ID of the admin performing the action
            action: Type of action (e.g., 'toggle_admin', 'deactivate')
            user_id: ID of the user being acted upon
            details: Additional details about the action
        """
        logger = self._get_logger("user_management")
        
        log_data = {
            "admin_id": admin_id,
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        logger.info(f"ADMIN_ACTION: {json.dumps(log_data)}")
    
    def log_dashboard_access(self, admin_id: int, section: str):
        """
        Log admin dashboard access events
        
        Args:
            admin_id: ID of the admin accessing the dashboard
            section: Dashboard section being accessed (e.g., 'overview', 'users')
        """
        logger = self._get_logger("dashboard_access")
        
        log_data = {
            "admin_id": admin_id,
            "section": section,
            "timestamp": datetime.now().isoformat()
        }
        
        message = f"DASHBOARD_ACCESS: {json.dumps(log_data)}"
        logger.info(message)
        
        # In production, store logs in memory
        if self.is_production:
            self._store_log_in_memory({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "type": "DASHBOARD_ACCESS",
                "data": log_data,
                "file": "in_memory"
            })
    
    def log_activity_view(self, admin_id: int, filters: Optional[Dict[str, Any]] = None):
        """
        Log when admins view activity logs
        
        Args:
            admin_id: ID of the admin viewing the logs
            filters: Any filters applied to the activity logs
        """
        logger = self._get_logger("activity_view")
        
        log_data = {
            "admin_id": admin_id,
            "filters": filters or {},
            "timestamp": datetime.now().isoformat()
        }
        
        message = f"ACTIVITY_VIEW: {json.dumps(log_data)}"
        logger.info(message)
        
        # In production, store logs in memory
        if self.is_production:
            self._store_log_in_memory({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "type": "ACTIVITY_VIEW",
                "data": log_data,
                "file": "in_memory"
            })
    
    def log_admin_error(self, admin_id: Optional[int], operation: str, error_message: str, details: Optional[Dict[str, Any]] = None):
        """
        Log errors occurring during admin operations
        
        Args:
            admin_id: ID of the admin (if known)
            operation: Operation during which the error occurred
            error_message: Error message
            details: Additional details about the error
        """
        logger = self._get_logger("errors")
        
        log_data = {
            "admin_id": admin_id,
            "operation": operation,
            "error": error_message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        message = f"ADMIN_ERROR: {json.dumps(log_data)}"
        logger.error(message)
        
        # In production, store logs in memory
        if self.is_production:
            self._store_log_in_memory({
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "type": "ADMIN_ERROR",
                "data": log_data,
                "file": "in_memory"
            })
    
    def _store_log_in_memory(self, log_entry: Dict[str, Any]):
        """
        Store log entry in memory for production environments
        
        Args:
            log_entry: The log entry to store
        """
        # Add to in-memory logs (limited to 1000 entries)
        self.in_memory_logs.append(log_entry)
        if len(self.in_memory_logs) > 1000:
            self.in_memory_logs.pop(0)  # Remove oldest log if we exceed limit
    
    def log_user_activity(self, admin_id: int, action: str, user_id: int, details: Optional[Dict[str, Any]] = None):
        """
        Log user management activities performed by admins
        
        Args:
            admin_id: ID of the admin performing the action
            action: Type of action (e.g., 'toggle_admin', 'deactivate')
            user_id: ID of the user being acted upon
            details: Additional details about the action
        """
        logger = self._get_logger("user_management")
        
        log_data = {
            "admin_id": admin_id,
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        message = f"ADMIN_ACTION: {json.dumps(log_data)}"
        logger.info(message)
        
        # In production, store logs in memory
        if self.is_production:
            self._store_log_in_memory({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "type": "ADMIN_ACTION",
                "data": log_data,
                "file": "in_memory"
            })
        
    def get_recent_admin_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent admin activity logs
        
        Args:
            count: Maximum number of logs to retrieve
            
        Returns:
            List of log entries as dictionaries
        """
        # In production, use in-memory logs
        if self.is_production:
            return self.in_memory_logs[-count:] if self.in_memory_logs else []
        
        # In development, read from files if available
        if not self.log_dir:
            return []
            
        logs = []
        
        try:
            # Get all log files in the directory
            log_files = []
            for root, _, files in os.walk(self.log_dir):
                for file in files:
                    if file.endswith('.log'):
                        log_files.append(os.path.join(root, file))
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Read log entries
            entries_count = 0
            for log_file in log_files:
                if entries_count >= count:
                    break
                    
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if entries_count >= count:
                                break
                                
                            # Parse log entry
                            parts = line.strip().split(' - ', 2)
                            if len(parts) == 3:
                                timestamp, level, message = parts
                                
                                # Try to extract JSON data
                                log_type = None
                                log_data = {}
                                
                                if ': {' in message:
                                    log_type, json_str = message.split(': ', 1)
                                    try:
                                        log_data = json.loads(json_str)
                                    except json.JSONDecodeError:
                                        log_data = {"raw_message": message}
                                else:
                                    log_data = {"raw_message": message}
                                    
                                logs.append({
                                    "timestamp": timestamp,
                                    "level": level,
                                    "type": log_type,
                                    "data": log_data,
                                    "file": os.path.basename(log_file)
                                })
                                
                                entries_count += 1
                except Exception as e:
                    # Log the error but continue processing other files
                    self.logger.error(f"Error reading log file {log_file}: {e}")
            
            return logs
        except Exception as e:
            self.logger.error(f"Error getting recent admin logs: {e}")
            return []

# Create a singleton instance
admin_logger = AdminLogger()
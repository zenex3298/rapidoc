import os
import logging
import time
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logger = logging.getLogger(__name__)

class PerformanceLogger:
    """
    Utility for tracking and logging performance metrics in various components.
    Helps diagnose timeout and performance issues by providing detailed timing information.
    """
    
    def __init__(self, component: str):
        """
        Initialize a performance logger for a specific component.
        
        Args:
            component: The name of the component being monitored (e.g., 'document_service', 'openai_service')
        """
        self.component = component
        self.start_times: Dict[str, float] = {}
        self.timings: Dict[str, List[Dict[str, Any]]] = {}
        self.session_id = str(uuid.uuid4())[:8]  # Create a short session ID for correlation
        
        # Set up component-specific log file
        log_dir = os.path.join('logs', 'performance')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a handler for the component log file
        today = datetime.now().strftime('%Y-%m-%d')
        component_file = os.path.join(log_dir, f'{component}_{today}.log')
        
        # Add file handler to this logger
        self.logger = logging.getLogger(f'performance.{component}')
        if not self.logger.handlers:
            file_handler = logging.FileHandler(component_file)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Started performance logging for session {self.session_id}")
    
    def start_timer(self, operation: str, details: Optional[Dict[str, Any]] = None) -> str:
        """
        Start timing an operation.
        
        Args:
            operation: Name of the operation being timed
            details: Additional details about the operation
            
        Returns:
            str: Timer ID for stopping the timer later
        """
        timer_id = f"{operation}_{uuid.uuid4()}"
        self.start_times[timer_id] = time.time()
        
        # Log the start of the operation
        log_data = {
            "session_id": self.session_id,
            "component": self.component,
            "operation": operation,
            "action": "start",
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.logger.info(f"START {operation} - {json.dumps(log_data)}")
        return timer_id
    
    def stop_timer(self, timer_id: str, details: Optional[Dict[str, Any]] = None) -> float:
        """
        Stop timing an operation and record the result.
        
        Args:
            timer_id: Timer ID returned from start_timer
            details: Additional details about the operation result
            
        Returns:
            float: Elapsed time in seconds
        """
        if timer_id not in self.start_times:
            self.logger.warning(f"Timer ID {timer_id} not found")
            return 0.0
        
        # Calculate elapsed time
        elapsed_time = time.time() - self.start_times[timer_id]
        
        # Extract operation name from timer_id
        operation = timer_id.split('_')[0]
        
        # Record the timing
        if operation not in self.timings:
            self.timings[operation] = []
        
        timing_record = {
            "timer_id": timer_id,
            "elapsed_seconds": elapsed_time,
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            timing_record["details"] = details
            
        self.timings[operation].append(timing_record)
        
        # Log the end of the operation
        log_data = {
            "session_id": self.session_id,
            "component": self.component,
            "operation": operation,
            "action": "stop",
            "elapsed_seconds": elapsed_time,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        # Add warning flag for operations taking more than 20 seconds
        if elapsed_time > 20:
            log_data["warning"] = f"Operation took {elapsed_time:.2f} seconds (exceeds 20s threshold)"
            self.logger.warning(f"SLOW {operation} - {json.dumps(log_data)}")
        else:
            self.logger.info(f"STOP {operation} - {json.dumps(log_data)}")
        
        # Clean up
        del self.start_times[timer_id]
        
        return elapsed_time
    
    def log_threshold_exceeded(self, operation: str, threshold_seconds: float, 
                              details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log when an operation exceeds a certain time threshold.
        
        Args:
            operation: Name of the operation
            threshold_seconds: Threshold in seconds that was exceeded
            details: Additional details about the threshold event
        """
        log_data = {
            "session_id": self.session_id,
            "component": self.component,
            "operation": operation,
            "action": "threshold_exceeded",
            "threshold_seconds": threshold_seconds,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.logger.warning(f"THRESHOLD EXCEEDED {operation} - {json.dumps(log_data)}")

    def log_operation_failed(self, operation: str, error: Exception, 
                           elapsed_seconds: Optional[float] = None,
                           details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log when an operation fails.
        
        Args:
            operation: Name of the operation
            error: The exception that occurred
            elapsed_seconds: Optional elapsed time before failure
            details: Additional details about the failure
        """
        log_data = {
            "session_id": self.session_id,
            "component": self.component,
            "operation": operation,
            "action": "failed",
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat()
        }
        
        if elapsed_seconds is not None:
            log_data["elapsed_seconds"] = elapsed_seconds
            
        if details:
            log_data["details"] = details
            
        self.logger.error(f"FAILED {operation} - {json.dumps(log_data)}")
    
    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for operations performed.
        
        Args:
            operation: Optional specific operation to get stats for
            
        Returns:
            Dict[str, Any]: Statistics for the specified operation or all operations
        """
        stats = {}
        
        # If operation specified, only return stats for that operation
        if operation:
            if operation in self.timings:
                operation_times = [record["elapsed_seconds"] for record in self.timings[operation]]
                if operation_times:
                    stats[operation] = {
                        "count": len(operation_times),
                        "total_seconds": sum(operation_times),
                        "average_seconds": sum(operation_times) / len(operation_times),
                        "min_seconds": min(operation_times),
                        "max_seconds": max(operation_times)
                    }
            return stats
        
        # Otherwise return stats for all operations
        for op, records in self.timings.items():
            operation_times = [record["elapsed_seconds"] for record in records]
            if operation_times:
                stats[op] = {
                    "count": len(operation_times),
                    "total_seconds": sum(operation_times),
                    "average_seconds": sum(operation_times) / len(operation_times),
                    "min_seconds": min(operation_times),
                    "max_seconds": max(operation_times)
                }
        
        return stats
    
    def log_statistics(self) -> None:
        """Log statistics for all operations."""
        stats = self.get_statistics()
        
        log_data = {
            "session_id": self.session_id,
            "component": self.component,
            "action": "statistics",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats
        }
        
        self.logger.info(f"STATISTICS - {json.dumps(log_data)}")

# Create performance logger instances for various components
document_perf_logger = PerformanceLogger("document_service")
openai_perf_logger = PerformanceLogger("openai_service")
api_perf_logger = PerformanceLogger("api_endpoints")
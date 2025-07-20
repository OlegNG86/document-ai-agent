"""Performance monitoring utilities."""

import time
import psutil
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from .logging_config import get_logger


logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_before: Optional[float] = None
    memory_after: Optional[float] = None
    memory_delta: Optional[float] = None
    cpu_percent: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, success: bool = True, error: Optional[str] = None):
        """Mark operation as finished and calculate metrics."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error
        
        # Get memory usage after operation
        try:
            process = psutil.Process()
            self.memory_after = process.memory_info().rss / 1024 / 1024  # MB
            if self.memory_before is not None:
                self.memory_delta = self.memory_after - self.memory_before
        except Exception:
            pass


class PerformanceMonitor:
    """Performance monitoring system."""
    
    def __init__(self, slow_threshold: float = 5.0, memory_threshold: float = 500.0):
        """Initialize performance monitor.
        
        Args:
            slow_threshold: Threshold in seconds for slow operations.
            memory_threshold: Memory usage threshold in MB.
        """
        self.slow_threshold = slow_threshold
        self.memory_threshold = memory_threshold
        self.metrics_history: deque = deque(maxlen=1000)
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'avg_duration': 0.0,
            'min_duration': float('inf'),
            'max_duration': 0.0,
            'success_count': 0,
            'error_count': 0,
            'last_execution': None
        })
        self._lock = threading.Lock()
        
        # Start background monitoring
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._background_monitor, daemon=True)
        self._monitor_thread.start()
    
    def start_operation(self, operation: str, **metadata) -> PerformanceMetrics:
        """Start monitoring an operation.
        
        Args:
            operation: Operation name.
            **metadata: Additional metadata.
            
        Returns:
            PerformanceMetrics instance.
        """
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            metadata=metadata
        )
        
        # Get initial memory usage
        try:
            process = psutil.Process()
            metrics.memory_before = process.memory_info().rss / 1024 / 1024  # MB
            metrics.cpu_percent = process.cpu_percent()
        except Exception:
            pass
        
        logger.debug(
            f"Started monitoring operation: {operation}",
            extra={
                'operation': operation,
                'memory_before': metrics.memory_before,
                'cpu_percent': metrics.cpu_percent,
                **metadata
            }
        )
        
        return metrics
    
    def finish_operation(self, metrics: PerformanceMetrics, success: bool = True, 
                        error: Optional[str] = None):
        """Finish monitoring an operation.
        
        Args:
            metrics: PerformanceMetrics instance from start_operation.
            success: Whether operation was successful.
            error: Error message if operation failed.
        """
        metrics.finish(success, error)
        
        with self._lock:
            # Add to history
            self.metrics_history.append(metrics)
            
            # Update operation statistics
            stats = self.operation_stats[metrics.operation]
            stats['count'] += 1
            stats['total_duration'] += metrics.duration
            stats['avg_duration'] = stats['total_duration'] / stats['count']
            stats['min_duration'] = min(stats['min_duration'], metrics.duration)
            stats['max_duration'] = max(stats['max_duration'], metrics.duration)
            stats['last_execution'] = datetime.now()
            
            if success:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1
        
        # Log performance metrics
        log_level = logging.WARNING if metrics.duration > self.slow_threshold else logging.DEBUG
        
        log_extra = {
            'operation': metrics.operation,
            'processing_time': metrics.duration,
            'success': success,
            'memory_before': metrics.memory_before,
            'memory_after': metrics.memory_after,
            'memory_delta': metrics.memory_delta,
            **metrics.metadata
        }
        
        if error:
            log_extra['error'] = error
        
        message = f"Operation {metrics.operation} completed in {metrics.duration:.2f}s"
        if metrics.duration > self.slow_threshold:
            message += " (SLOW)"
        if metrics.memory_delta and metrics.memory_delta > 50:  # 50MB threshold
            message += f" (Memory: +{metrics.memory_delta:.1f}MB)"
        
        logger.log(log_level, message, extra=log_extra)
        
        # Check for performance issues
        self._check_performance_issues(metrics)
    
    def _check_performance_issues(self, metrics: PerformanceMetrics):
        """Check for performance issues and log warnings."""
        issues = []
        
        # Check slow operations
        if metrics.duration > self.slow_threshold:
            issues.append(f"Slow operation: {metrics.duration:.2f}s > {self.slow_threshold}s")
        
        # Check memory usage
        if metrics.memory_after and metrics.memory_after > self.memory_threshold:
            issues.append(f"High memory usage: {metrics.memory_after:.1f}MB > {self.memory_threshold}MB")
        
        # Check memory leaks
        if metrics.memory_delta and metrics.memory_delta > 100:  # 100MB increase
            issues.append(f"Potential memory leak: +{metrics.memory_delta:.1f}MB")
        
        if issues:
            logger.warning(
                f"Performance issues detected in {metrics.operation}: {'; '.join(issues)}",
                extra={
                    'operation': metrics.operation,
                    'performance_issues': issues,
                    'processing_time': metrics.duration,
                    'memory_usage': metrics.memory_after,
                    'memory_delta': metrics.memory_delta
                }
            )
    
    def _background_monitor(self):
        """Background monitoring thread."""
        while self._monitoring_active:
            try:
                # Monitor system resources
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Log system metrics periodically (every 5 minutes)
                if int(time.time()) % 300 == 0:
                    logger.info(
                        "System resource usage",
                        extra={
                            'operation': 'system_monitor',
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory.percent,
                            'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                            'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                            'disk_percent': (disk.used / disk.total) * 100
                        }
                    )
                
                # Check for resource issues
                if cpu_percent > 90:
                    logger.warning(f"High CPU usage: {cpu_percent}%")
                
                if memory.percent > 90:
                    logger.warning(f"High memory usage: {memory.percent}%")
                
                if (disk.used / disk.total) > 0.9:
                    logger.warning(f"Low disk space: {(disk.free / 1024 / 1024 / 1024):.1f}GB free")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in background monitoring: {e}")
                time.sleep(60)
    
    def get_operation_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get operation statistics.
        
        Args:
            operation: Specific operation name, or None for all operations.
            
        Returns:
            Operation statistics.
        """
        with self._lock:
            if operation:
                return dict(self.operation_stats.get(operation, {}))
            else:
                return {op: dict(stats) for op, stats in self.operation_stats.items()}
    
    def get_recent_metrics(self, operation: Optional[str] = None, 
                          limit: int = 100) -> list:
        """Get recent performance metrics.
        
        Args:
            operation: Filter by operation name.
            limit: Maximum number of metrics to return.
            
        Returns:
            List of recent metrics.
        """
        with self._lock:
            metrics = list(self.metrics_history)
            
            if operation:
                metrics = [m for m in metrics if m.operation == operation]
            
            return metrics[-limit:]
    
    def get_slow_operations(self, threshold: Optional[float] = None) -> list:
        """Get operations that exceeded the slow threshold.
        
        Args:
            threshold: Custom threshold, or None to use default.
            
        Returns:
            List of slow operations.
        """
        threshold = threshold or self.slow_threshold
        
        with self._lock:
            return [
                m for m in self.metrics_history 
                if m.duration and m.duration > threshold
            ]
    
    def reset_stats(self):
        """Reset all statistics."""
        with self._lock:
            self.metrics_history.clear()
            self.operation_stats.clear()
        
        logger.info("Performance statistics reset")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._monitoring_active = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


class performance_tracker:
    """Context manager for tracking operation performance."""
    
    def __init__(self, operation: str, **metadata):
        """Initialize performance tracker.
        
        Args:
            operation: Operation name.
            **metadata: Additional metadata.
        """
        self.operation = operation
        self.metadata = metadata
        self.metrics = None
    
    def __enter__(self) -> PerformanceMetrics:
        """Start performance tracking."""
        self.metrics = performance_monitor.start_operation(self.operation, **self.metadata)
        return self.metrics
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish performance tracking."""
        success = exc_type is None
        error = str(exc_val) if exc_val else None
        performance_monitor.finish_operation(self.metrics, success, error)


def monitor_performance(operation: str, **metadata):
    """Decorator for monitoring function performance.
    
    Args:
        operation: Operation name.
        **metadata: Additional metadata.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with performance_tracker(operation, **metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator
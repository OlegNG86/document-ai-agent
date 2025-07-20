"""Health monitoring and system diagnostics."""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .logging_config import get_logger
from .error_handling import error_notification_manager, create_error, ErrorCategory, ErrorSeverity


logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    response_time: Optional[float] = None


class HealthMonitor:
    """System health monitoring."""
    
    def __init__(self, check_interval: int = 60):
        """Initialize health monitor.
        
        Args:
            check_interval: Health check interval in seconds.
        """
        self.check_interval = check_interval
        self.health_checks: Dict[str, Callable[[], HealthCheck]] = {}
        self.health_history: List[HealthCheck] = []
        self.max_history_size = 1000
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # System thresholds
        self.cpu_warning_threshold = 80.0
        self.cpu_critical_threshold = 95.0
        self.memory_warning_threshold = 80.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 85.0
        self.disk_critical_threshold = 95.0
        
        # Register default health checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default system health checks."""
        self.register_health_check("system_cpu", self._check_cpu_usage)
        self.register_health_check("system_memory", self._check_memory_usage)
        self.register_health_check("system_disk", self._check_disk_usage)
        self.register_health_check("system_processes", self._check_process_health)
    
    def register_health_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """Register a health check function.
        
        Args:
            name: Health check name.
            check_func: Function that returns HealthCheck.
        """
        self.health_checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    def start_monitoring(self):
        """Start background health monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring."""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                self.run_all_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(self.check_interval)
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks.
        
        Returns:
            Dictionary of health check results.
        """
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = check_func()
                result.response_time = time.time() - start_time
                results[name] = result
                
                # Add to history
                self.health_history.append(result)
                if len(self.health_history) > self.max_history_size:
                    self.health_history = self.health_history[-self.max_history_size:]
                
                # Log critical issues
                if result.status == HealthStatus.CRITICAL:
                    logger.critical(
                        f"Critical health issue: {result.name} - {result.message}",
                        extra={
                            'health_check': result.name,
                            'status': result.status.value,
                            'details': result.details,
                            'response_time': result.response_time
                        }
                    )
                    
                    # Create error notification
                    error = create_error(
                        error_code=f"HEALTH_CHECK_CRITICAL_{result.name.upper()}",
                        message=f"Critical health issue in {result.name}: {result.message}",
                        category=ErrorCategory.RESOURCE,
                        severity=ErrorSeverity.CRITICAL,
                        details=result.details,
                        suggestions=self._get_health_suggestions(result)
                    )
                
                elif result.status == HealthStatus.WARNING:
                    logger.warning(
                        f"Health warning: {result.name} - {result.message}",
                        extra={
                            'health_check': result.name,
                            'status': result.status.value,
                            'details': result.details,
                            'response_time': result.response_time
                        }
                    )
                
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = HealthCheck(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {e}",
                    details={'error': str(e)},
                    timestamp=datetime.now()
                )
        
        return results
    
    def _get_health_suggestions(self, health_check: HealthCheck) -> List[str]:
        """Get suggestions for health issues.
        
        Args:
            health_check: Health check result.
            
        Returns:
            List of suggestions.
        """
        suggestions = []
        
        if health_check.name == "system_cpu":
            suggestions.extend([
                "Check for high CPU processes using 'top' or 'htop'",
                "Consider scaling up CPU resources",
                "Review application performance and optimization"
            ])
        elif health_check.name == "system_memory":
            suggestions.extend([
                "Check memory usage with 'free -h'",
                "Look for memory leaks in applications",
                "Consider increasing available memory",
                "Review memory-intensive operations"
            ])
        elif health_check.name == "system_disk":
            suggestions.extend([
                "Clean up temporary files and logs",
                "Archive or delete old data",
                "Check disk usage with 'df -h'",
                "Consider adding more storage"
            ])
        
        return suggestions
    
    def _check_cpu_usage(self) -> HealthCheck:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent >= self.cpu_critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Critical CPU usage: {cpu_percent:.1f}%"
            elif cpu_percent >= self.cpu_warning_threshold:
                status = HealthStatus.WARNING
                message = f"High CPU usage: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage normal: {cpu_percent:.1f}%"
            
            return HealthCheck(
                name="system_cpu",
                status=status,
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'cpu_count': psutil.cpu_count(),
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_cpu",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU usage: {e}",
                details={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent >= self.memory_critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Critical memory usage: {memory.percent:.1f}%"
            elif memory.percent >= self.memory_warning_threshold:
                status = HealthStatus.WARNING
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return HealthCheck(
                name="system_memory",
                status=status,
                message=message,
                details={
                    'memory_percent': memory.percent,
                    'memory_total_gb': memory.total / 1024 / 1024 / 1024,
                    'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                    'memory_used_gb': memory.used / 1024 / 1024 / 1024
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_memory",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory usage: {e}",
                details={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _check_disk_usage(self) -> HealthCheck:
        """Check disk usage."""
        try:
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent >= self.disk_critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Critical disk usage: {disk_percent:.1f}%"
            elif disk_percent >= self.disk_warning_threshold:
                status = HealthStatus.WARNING
                message = f"High disk usage: {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {disk_percent:.1f}%"
            
            return HealthCheck(
                name="system_disk",
                status=status,
                message=message,
                details={
                    'disk_percent': disk_percent,
                    'disk_total_gb': disk.total / 1024 / 1024 / 1024,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                    'disk_used_gb': disk.used / 1024 / 1024 / 1024
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_disk",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk usage: {e}",
                details={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _check_process_health(self) -> HealthCheck:
        """Check process health."""
        try:
            current_process = psutil.Process()
            
            # Get process info
            process_info = {
                'pid': current_process.pid,
                'memory_mb': current_process.memory_info().rss / 1024 / 1024,
                'cpu_percent': current_process.cpu_percent(),
                'num_threads': current_process.num_threads(),
                'status': current_process.status(),
                'create_time': datetime.fromtimestamp(current_process.create_time()).isoformat()
            }
            
            # Check for issues
            issues = []
            if process_info['memory_mb'] > 1000:  # 1GB
                issues.append(f"High memory usage: {process_info['memory_mb']:.1f}MB")
            
            if process_info['num_threads'] > 50:
                issues.append(f"High thread count: {process_info['num_threads']}")
            
            if issues:
                status = HealthStatus.WARNING
                message = f"Process issues detected: {'; '.join(issues)}"
            else:
                status = HealthStatus.HEALTHY
                message = "Process health normal"
            
            return HealthCheck(
                name="system_processes",
                status=status,
                message=message,
                details=process_info,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_processes",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check process health: {e}",
                details={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary.
        
        Returns:
            Health summary dictionary.
        """
        recent_checks = {}
        overall_status = HealthStatus.HEALTHY
        
        # Get most recent check for each type
        for check in reversed(self.health_history):
            if check.name not in recent_checks:
                recent_checks[check.name] = check
        
        # Determine overall status
        for check in recent_checks.values():
            if check.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                break
            elif check.status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.WARNING
            elif check.status == HealthStatus.UNKNOWN and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.UNKNOWN
        
        return {
            'overall_status': overall_status.value,
            'last_check': max(check.timestamp for check in recent_checks.values()) if recent_checks else None,
            'checks': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'timestamp': check.timestamp.isoformat(),
                    'response_time': check.response_time
                }
                for name, check in recent_checks.items()
            },
            'monitoring_active': self.monitoring_active
        }


# Global health monitor instance
health_monitor = HealthMonitor()
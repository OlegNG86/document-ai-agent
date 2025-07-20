"""Enhanced error handling utilities with retry mechanisms."""

import time
import random
import logging
from typing import Optional, Callable, Any, Type, Union, List, Dict
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

# Import logger after other imports to avoid circular imports
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    NETWORK = "network"
    VALIDATION = "validation"
    PROCESSING = "processing"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"
    USER_INPUT = "user_input"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    retry_after: Optional[float] = None


class AIAgentError(Exception):
    """Base exception class for AI Agent errors."""
    
    def __init__(self, error_info: ErrorInfo, original_error: Optional[Exception] = None):
        """Initialize AI Agent error.
        
        Args:
            error_info: Structured error information.
            original_error: Original exception that caused this error.
        """
        self.error_info = error_info
        self.original_error = original_error
        super().__init__(error_info.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            'error_code': self.error_info.error_code,
            'message': self.error_info.message,
            'category': self.error_info.category.value,
            'severity': self.error_info.severity.value,
            'details': self.error_info.details or {},
            'suggestions': self.error_info.suggestions or [],
            'retry_after': self.error_info.retry_after,
            'original_error': str(self.original_error) if self.original_error else None
        }


class NetworkError(AIAgentError):
    """Network-related errors."""
    pass


class ValidationError(AIAgentError):
    """Validation errors."""
    pass


class ProcessingError(AIAgentError):
    """Processing errors."""
    pass


class ResourceError(AIAgentError):
    """Resource-related errors."""
    pass


class ConfigurationError(AIAgentError):
    """Configuration errors."""
    pass


class ExternalServiceError(AIAgentError):
    """External service errors."""
    pass


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_strategy: str = "exponential",
        timeout: Optional[float] = None,
        retry_on_timeout: bool = True
    ):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts.
            base_delay: Base delay between retries in seconds.
            max_delay: Maximum delay between retries in seconds.
            exponential_base: Base for exponential backoff.
            jitter: Whether to add random jitter to delays.
            backoff_strategy: Backoff strategy ('exponential', 'linear', 'fixed').
            timeout: Operation timeout in seconds.
            retry_on_timeout: Whether to retry on timeout errors.
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_strategy = backoff_strategy
        self.timeout = timeout
        self.retry_on_timeout = retry_on_timeout
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt.
        
        Args:
            attempt: Current attempt number (0-based).
            
        Returns:
            Delay in seconds.
        """
        if self.backoff_strategy == "exponential":
            delay = self.base_delay * (self.exponential_base ** attempt)
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * (attempt + 1)
        else:  # fixed
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Time to wait before attempting recovery.
            expected_exception: Exception type that triggers circuit breaker.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection.
        
        Args:
            func: Function to call.
            *args: Function arguments.
            **kwargs: Function keyword arguments.
            
        Returns:
            Function result.
            
        Raises:
            Exception: If circuit is open or function fails.
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise ExternalServiceError(
                    ErrorInfo(
                        error_code="CIRCUIT_BREAKER_OPEN",
                        message="Circuit breaker is open - service unavailable",
                        category=ErrorCategory.EXTERNAL_SERVICE,
                        severity=ErrorSeverity.HIGH,
                        retry_after=self.recovery_timeout
                    )
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


def is_network_error(exception: Exception) -> bool:
    """Check if exception is a network-related error.
    
    Args:
        exception: Exception to check.
        
    Returns:
        True if it's a network error.
    """
    network_error_types = (
        ConnectionError,
        socket.error,
        socket.timeout,
        TimeoutError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
    )
    
    if isinstance(exception, network_error_types):
        return True
    
    # Check error message for network-related keywords
    error_msg = str(exception).lower()
    network_keywords = [
        'connection', 'timeout', 'network', 'unreachable',
        'refused', 'reset', 'broken pipe', 'name resolution',
        'dns', 'host', 'port', 'socket'
    ]
    
    return any(keyword in error_msg for keyword in network_keywords)


def is_temporary_error(exception: Exception) -> bool:
    """Check if exception is likely temporary and worth retrying.
    
    Args:
        exception: Exception to check.
        
    Returns:
        True if it's likely a temporary error.
    """
    if is_network_error(exception):
        return True
    
    # Check for temporary error indicators
    error_msg = str(exception).lower()
    temporary_keywords = [
        'temporary', 'busy', 'overloaded', 'rate limit',
        'service unavailable', 'internal server error',
        'bad gateway', 'gateway timeout', 'too many requests'
    ]
    
    return any(keyword in error_msg for keyword in temporary_keywords)


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    exceptions: Union[Type[Exception], tuple] = Exception,
    logger: Optional[logging.Logger] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None
):
    """Decorator for adding retry logic to functions.
    
    Args:
        retry_config: Retry configuration.
        exceptions: Exception types to retry on.
        logger: Logger for retry attempts.
        should_retry: Custom function to determine if error should be retried.
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            start_time = time.time()
            
            for attempt in range(retry_config.max_attempts):
                try:
                    # Apply timeout if configured
                    if retry_config.timeout:
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError(f"Operation timed out after {retry_config.timeout}s")
                        
                        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(int(retry_config.timeout))
                        
                        try:
                            result = func(*args, **kwargs)
                            signal.alarm(0)  # Cancel timeout
                            signal.signal(signal.SIGALRM, old_handler)
                            return result
                        except:
                            signal.alarm(0)  # Cancel timeout
                            signal.signal(signal.SIGALRM, old_handler)
                            raise
                    else:
                        return func(*args, **kwargs)
                        
                except exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry this error
                    if should_retry and not should_retry(e):
                        if logger:
                            logger.info(
                                f"Not retrying {func.__name__} due to non-retryable error: {e}",
                                extra={'operation': func.__name__, 'error': str(e)}
                            )
                        break
                    
                    # For timeout errors, check if we should retry
                    if isinstance(e, TimeoutError) and not retry_config.retry_on_timeout:
                        if logger:
                            logger.info(
                                f"Not retrying {func.__name__} due to timeout (retry_on_timeout=False)",
                                extra={'operation': func.__name__, 'timeout': retry_config.timeout}
                            )
                        break
                    
                    if attempt == retry_config.max_attempts - 1:
                        # Last attempt failed
                        total_time = time.time() - start_time
                        if logger:
                            logger.error(
                                f"All retry attempts failed for {func.__name__} after {total_time:.2f}s",
                                extra={
                                    'operation': func.__name__,
                                    'total_attempts': retry_config.max_attempts,
                                    'total_time': total_time,
                                    'final_error': str(e),
                                    'error_type': type(e).__name__,
                                    'is_network_error': is_network_error(e),
                                    'is_temporary_error': is_temporary_error(e)
                                }
                            )
                        break
                    
                    # Calculate delay and wait
                    delay = retry_config.calculate_delay(attempt)
                    
                    if logger:
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{retry_config.max_attempts} "
                            f"for {func.__name__} after {delay:.2f}s: {e}",
                            extra={
                                'operation': func.__name__,
                                'retry_count': attempt + 1,
                                'delay': delay,
                                'error': str(e),
                                'error_type': type(e).__name__,
                                'is_network_error': is_network_error(e),
                                'is_temporary_error': is_temporary_error(e)
                            }
                        )
                    
                    time.sleep(delay)
            
            # All attempts failed
            raise last_exception
        
        return wrapper
    return decorator


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """Decorator for adding circuit breaker protection.
    
    Args:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout: Time to wait before attempting recovery.
        expected_exception: Exception type that triggers circuit breaker.
    """
    circuit_breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


class ErrorNotificationManager:
    """Centralized error notification system."""
    
    def __init__(self):
        """Initialize error notification manager."""
        self.logger = logging.getLogger(__name__)
        self.error_handlers: List[Callable[[AIAgentError], None]] = []
        self.error_stats: Dict[str, Dict[str, Any]] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Error rate tracking
        self.error_rate_window = timedelta(minutes=5)
        self.error_rate_threshold = 10  # errors per window
        
        # Setup default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default error handlers."""
        # Add console error handler for critical errors
        self.add_error_handler(self._console_error_handler)
        
        # Add error rate monitoring handler
        self.add_error_handler(self._error_rate_handler)
    
    def _console_error_handler(self, error: AIAgentError):
        """Default console error handler for critical errors."""
        if error.error_info.severity == ErrorSeverity.CRITICAL:
            print(f"\n🚨 CRITICAL ERROR: {error.error_info.message}")
            if error.error_info.suggestions:
                print("💡 Suggestions:")
                for suggestion in error.error_info.suggestions:
                    print(f"  • {suggestion}")
    
    def _error_rate_handler(self, error: AIAgentError):
        """Monitor error rate and alert on high error rates."""
        now = datetime.now()
        recent_errors = [
            e for e in self.error_history 
            if now - e['timestamp'] <= self.error_rate_window
        ]
        
        if len(recent_errors) >= self.error_rate_threshold:
            self.logger.critical(
                f"High error rate detected: {len(recent_errors)} errors in {self.error_rate_window}",
                extra={
                    'operation': 'error_rate_monitoring',
                    'error_count': len(recent_errors),
                    'time_window_minutes': self.error_rate_window.total_seconds() / 60,
                    'recent_error_codes': [e['error_code'] for e in recent_errors[-5:]]
                }
            )
    
    def add_error_handler(self, handler: Callable[[AIAgentError], None]):
        """Add error handler.
        
        Args:
            handler: Function to handle errors.
        """
        self.error_handlers.append(handler)
    
    def notify_error(self, error: AIAgentError, context: Optional[Dict[str, Any]] = None):
        """Notify about an error.
        
        Args:
            error: Error to notify about.
            context: Additional context information.
        """
        error_code = error.error_info.error_code
        now = datetime.now()
        
        # Update error statistics
        if error_code not in self.error_stats:
            self.error_stats[error_code] = {
                'count': 0,
                'first_occurrence': now,
                'last_occurrence': now,
                'category': error.error_info.category.value,
                'severity': error.error_info.severity.value
            }
        
        self.error_stats[error_code]['count'] += 1
        self.error_stats[error_code]['last_occurrence'] = now
        
        # Add to error history
        error_record = {
            'timestamp': now,
            'error_code': error_code,
            'message': error.error_info.message,
            'category': error.error_info.category.value,
            'severity': error.error_info.severity.value,
            'context': context or {}
        }
        
        self.error_history.append(error_record)
        
        # Trim history if too large
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        # Log the error with enhanced context
        log_extra = {
            'error_code': error_code,
            'category': error.error_info.category.value,
            'severity': error.error_info.severity.value,
            'error_count': self.error_stats[error_code]['count'],
            'first_occurrence': self.error_stats[error_code]['first_occurrence'].isoformat(),
            'suggestions': error.error_info.suggestions or []
        }
        
        if context:
            log_extra.update(context)
        
        # Choose log level based on severity and frequency
        if error.error_info.severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif error.error_info.severity == ErrorSeverity.HIGH:
            log_level = logging.ERROR
        elif self.error_stats[error_code]['count'] > 5:  # Frequent error
            log_level = logging.ERROR
        else:
            log_level = logging.WARNING
        
        self.logger.log(
            log_level,
            f"Error occurred: {error.error_info.message}",
            extra=log_extra,
            exc_info=error.original_error if log_level >= logging.ERROR else None
        )
        
        # Call registered error handlers
        for handler in self.error_handlers:
            try:
                handler(error)
            except Exception as e:
                self.logger.error(f"Error handler failed: {e}")
    
    def get_error_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get error statistics.
        
        Returns:
            Dictionary with error statistics by error code.
        """
        return {
            code: {
                **stats,
                'first_occurrence': stats['first_occurrence'].isoformat(),
                'last_occurrence': stats['last_occurrence'].isoformat()
            }
            for code, stats in self.error_stats.items()
        }
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors.
        
        Args:
            limit: Maximum number of errors to return.
            
        Returns:
            List of recent error records.
        """
        return [
            {
                **error,
                'timestamp': error['timestamp'].isoformat()
            }
            for error in self.error_history[-limit:]
        ]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics.
        
        Returns:
            Summary of error statistics.
        """
        total_errors = sum(stats['count'] for stats in self.error_stats.values())
        
        # Count by severity
        severity_counts = {}
        for stats in self.error_stats.values():
            severity = stats['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + stats['count']
        
        # Count by category
        category_counts = {}
        for stats in self.error_stats.values():
            category = stats['category']
            category_counts[category] = category_counts.get(category, 0) + stats['count']
        
        # Recent error rate
        now = datetime.now()
        recent_errors = [
            e for e in self.error_history 
            if now - e['timestamp'] <= self.error_rate_window
        ]
        
        return {
            'total_errors': total_errors,
            'unique_error_codes': len(self.error_stats),
            'severity_breakdown': severity_counts,
            'category_breakdown': category_counts,
            'recent_error_rate': len(recent_errors),
            'error_rate_window_minutes': self.error_rate_window.total_seconds() / 60,
            'most_frequent_errors': sorted(
                [(code, stats['count']) for code, stats in self.error_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def clear_error_stats(self):
        """Clear error statistics."""
        self.error_stats.clear()
        self.error_history.clear()
        self.logger.info("Error statistics cleared")


# Global error notification manager
error_notification_manager = ErrorNotificationManager()


def handle_error(
    error: Exception,
    error_code: str,
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> AIAgentError:
    """Handle and convert exception to AIAgentError.
    
    Args:
        error: Original exception.
        error_code: Error code.
        category: Error category.
        severity: Error severity.
        details: Additional error details.
        suggestions: Suggestions for fixing the error.
        context: Context information.
        
    Returns:
        AIAgentError instance.
    """
    error_info = ErrorInfo(
        error_code=error_code,
        message=str(error),
        category=category,
        severity=severity,
        details=details,
        suggestions=suggestions
    )
    
    ai_error = AIAgentError(error_info, error)
    error_notification_manager.notify_error(ai_error, context)
    
    return ai_error


def create_error(
    error_code: str,
    message: str,
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> AIAgentError:
    """Create a new AIAgentError.
    
    Args:
        error_code: Error code.
        message: Error message.
        category: Error category.
        severity: Error severity.
        details: Additional error details.
        suggestions: Suggestions for fixing the error.
        context: Context information.
        
    Returns:
        AIAgentError instance.
    """
    error_info = ErrorInfo(
        error_code=error_code,
        message=message,
        category=category,
        severity=severity,
        details=details,
        suggestions=suggestions
    )
    
    ai_error = AIAgentError(error_info)
    error_notification_manager.notify_error(ai_error, context)
    
    return ai_error


# Common error configurations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    timeout=30.0,
    retry_on_timeout=True
)

OLLAMA_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=1.5,
    jitter=True,
    timeout=120.0,
    retry_on_timeout=True
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=False,
    timeout=30.0,
    retry_on_timeout=False
)

FILE_IO_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=False,
    timeout=10.0,
    retry_on_timeout=False
)

EMBEDDING_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=1.5,
    max_delay=45.0,
    exponential_base=1.8,
    jitter=True,
    timeout=90.0,
    retry_on_timeout=True
)
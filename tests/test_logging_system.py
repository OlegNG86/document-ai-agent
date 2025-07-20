"""Tests for the enhanced logging and error handling system."""

import pytest
import logging
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

from ai_agent.utils.logging_config import (
    LoggingManager, CustomFormatter, JSONFormatter, 
    get_logger, OperationLogger
)
from ai_agent.utils.error_handling import (
    AIAgentError, ErrorInfo, ErrorCategory, ErrorSeverity,
    RetryConfig, with_retry, CircuitBreaker, 
    handle_error, create_error, error_notification_manager
)
from ai_agent.utils.performance_monitor import (
    PerformanceMonitor, PerformanceMetrics, performance_tracker,
    monitor_performance
)


class TestLoggingSystem:
    """Test logging system functionality."""
    
    def test_custom_formatter_console(self):
        """Test custom formatter for console output."""
        formatter = CustomFormatter(use_colors=False, include_extra=True)
        
        # Create log record with extra fields
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.session_id = "test-session"
        record.processing_time = 1.23
        
        formatted = formatter.format(record)
        
        assert "Test message" in formatted
        assert "session=test-session" in formatted
        assert "time=1.23s" in formatted
    
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.document_id = "test-doc"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["document_id"] == "test-doc"
        assert "timestamp" in data
    
    def test_logging_manager_initialization(self):
        """Test logging manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {
                'LOG_DIR': temp_dir,
                'LOG_LEVEL': 'DEBUG',
                'ENABLE_FILE_LOGGING': 'true'
            }):
                manager = LoggingManager()
                logger = manager.get_logger("test")
                
                assert isinstance(logger, logging.Logger)
                assert logger.level <= logging.DEBUG
    
    def test_operation_logger(self):
        """Test operation logger with context."""
        base_logger = logging.getLogger("test")
        context = {"operation": "test_op", "session_id": "test-session"}
        
        op_logger = OperationLogger(base_logger, context)
        
        with patch.object(base_logger, 'log') as mock_log:
            op_logger.info("Test message", extra_field="value")
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            
            assert args[0] == logging.INFO
            assert args[1] == "Test message"
            assert kwargs['extra']['operation'] == "test_op"
            assert kwargs['extra']['session_id'] == "test-session"
            assert kwargs['extra']['extra_field'] == "value"


class TestErrorHandling:
    """Test error handling system."""
    
    def test_error_info_creation(self):
        """Test ErrorInfo creation."""
        error_info = ErrorInfo(
            error_code="TEST_ERROR",
            message="Test error message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            details={"field": "value"},
            suggestions=["Fix this", "Try that"]
        )
        
        assert error_info.error_code == "TEST_ERROR"
        assert error_info.category == ErrorCategory.VALIDATION
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.details["field"] == "value"
        assert len(error_info.suggestions) == 2
    
    def test_ai_agent_error(self):
        """Test AIAgentError creation and serialization."""
        error_info = ErrorInfo(
            error_code="TEST_ERROR",
            message="Test error",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.HIGH
        )
        
        original_error = ValueError("Original error")
        ai_error = AIAgentError(error_info, original_error)
        
        assert str(ai_error) == "Test error"
        assert ai_error.original_error == original_error
        
        error_dict = ai_error.to_dict()
        assert error_dict["error_code"] == "TEST_ERROR"
        assert error_dict["category"] == "processing"
        assert error_dict["severity"] == "high"
        assert error_dict["original_error"] == "Original error"
    
    def test_retry_config(self):
        """Test retry configuration."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            backoff_strategy="exponential",
            jitter=False  # Disable jitter for precise testing
        )
        
        # Test exponential backoff
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        
        # Test linear backoff
        config.backoff_strategy = "linear"
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 3.0
    
    def test_retry_decorator(self):
        """Test retry decorator functionality."""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            expected_exception=ValueError
        )
        
        def failing_function():
            raise ValueError("Always fails")
        
        # First failures should go through
        with pytest.raises(ValueError):
            circuit_breaker.call(failing_function)
        
        with pytest.raises(ValueError):
            circuit_breaker.call(failing_function)
        
        # Circuit should now be open
        assert circuit_breaker.state == "open"
        
        # Next call should raise circuit breaker error
        with pytest.raises(Exception) as exc_info:
            circuit_breaker.call(failing_function)
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    def test_handle_error(self):
        """Test error handling function."""
        original_error = ValueError("Original error")
        
        with patch.object(error_notification_manager, 'notify_error') as mock_notify:
            ai_error = handle_error(
                error=original_error,
                error_code="TEST_HANDLE_ERROR",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                details={"context": "test"},
                suggestions=["Fix it"]
            )
            
            assert isinstance(ai_error, AIAgentError)
            assert ai_error.error_info.error_code == "TEST_HANDLE_ERROR"
            assert ai_error.original_error == original_error
            mock_notify.assert_called_once()
    
    def test_create_error(self):
        """Test error creation function."""
        with patch.object(error_notification_manager, 'notify_error') as mock_notify:
            ai_error = create_error(
                error_code="TEST_CREATE_ERROR",
                message="Custom error message",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.CRITICAL
            )
            
            assert isinstance(ai_error, AIAgentError)
            assert ai_error.error_info.message == "Custom error message"
            assert ai_error.original_error is None
            mock_notify.assert_called_once()


class TestPerformanceMonitor:
    """Test performance monitoring system."""
    
    def test_performance_metrics(self):
        """Test performance metrics creation and finishing."""
        metrics = PerformanceMetrics(
            operation="test_operation",
            start_time=time.time(),
            metadata={"test": "value"}
        )
        
        assert metrics.operation == "test_operation"
        assert metrics.metadata["test"] == "value"
        assert metrics.end_time is None
        
        # Finish the operation
        metrics.finish(success=True)
        
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert metrics.success is True
        assert metrics.duration > 0
    
    def test_performance_monitor_operations(self):
        """Test performance monitor operation tracking."""
        monitor = PerformanceMonitor(slow_threshold=0.1)
        
        # Start and finish an operation
        metrics = monitor.start_operation("test_op", test_param="value")
        time.sleep(0.05)  # Small delay
        monitor.finish_operation(metrics, success=True)
        
        # Check statistics
        stats = monitor.get_operation_stats("test_op")
        assert stats["count"] == 1
        assert stats["success_count"] == 1
        assert stats["error_count"] == 0
        assert stats["avg_duration"] > 0
        
        # Test recent metrics
        recent = monitor.get_recent_metrics("test_op", limit=10)
        assert len(recent) == 1
        assert recent[0].operation == "test_op"
    
    def test_performance_tracker_context_manager(self):
        """Test performance tracker context manager."""
        with patch('ai_agent.utils.performance_monitor.performance_monitor') as mock_monitor:
            mock_metrics = Mock()
            mock_monitor.start_operation.return_value = mock_metrics
            
            with performance_tracker("test_operation", param="value") as metrics:
                assert metrics == mock_metrics
                time.sleep(0.01)
            
            mock_monitor.start_operation.assert_called_once_with("test_operation", param="value")
            mock_monitor.finish_operation.assert_called_once_with(mock_metrics, True, None)
    
    def test_performance_tracker_with_exception(self):
        """Test performance tracker with exception."""
        with patch('ai_agent.utils.performance_monitor.performance_monitor') as mock_monitor:
            mock_metrics = Mock()
            mock_monitor.start_operation.return_value = mock_metrics
            
            with pytest.raises(ValueError):
                with performance_tracker("test_operation"):
                    raise ValueError("Test error")
            
            mock_monitor.finish_operation.assert_called_once()
            args = mock_monitor.finish_operation.call_args[0]
            assert args[1] is False  # success=False
            assert "Test error" in args[2]  # error message
    
    def test_monitor_performance_decorator(self):
        """Test performance monitoring decorator."""
        with patch('ai_agent.utils.performance_monitor.performance_monitor') as mock_monitor:
            mock_metrics = Mock()
            mock_monitor.start_operation.return_value = mock_metrics
            
            @monitor_performance("decorated_operation", test_param="value")
            def test_function(x, y):
                return x + y
            
            result = test_function(1, 2)
            
            assert result == 3
            mock_monitor.start_operation.assert_called_once_with("decorated_operation", test_param="value")
            mock_monitor.finish_operation.assert_called_once_with(mock_metrics, True, None)
    
    def test_slow_operations_detection(self):
        """Test slow operations detection."""
        monitor = PerformanceMonitor(slow_threshold=0.05)
        
        # Fast operation
        metrics1 = monitor.start_operation("fast_op")
        time.sleep(0.01)
        monitor.finish_operation(metrics1, success=True)
        
        # Slow operation
        metrics2 = monitor.start_operation("slow_op")
        time.sleep(0.1)
        monitor.finish_operation(metrics2, success=True)
        
        slow_ops = monitor.get_slow_operations()
        assert len(slow_ops) == 1
        assert slow_ops[0].operation == "slow_op"
        assert slow_ops[0].duration > 0.05


class TestIntegration:
    """Integration tests for logging, error handling, and performance monitoring."""
    
    def test_logging_with_performance_tracking(self):
        """Test integration of logging with performance tracking."""
        logger = get_logger("test_integration")
        
        with patch.object(logger, 'info') as mock_info:
            with performance_tracker("integration_test", test_param="value"):
                logger.info("Operation in progress", extra={'step': 'middle'})
                time.sleep(0.01)
        
        # Check that logging was called
        mock_info.assert_called_once_with(
            "Operation in progress", 
            extra={'step': 'middle'}
        )
    
    def test_error_handling_with_logging(self):
        """Test error handling integration with logging."""
        # Mock the error notification manager's logger instead
        with patch('ai_agent.utils.error_handling.error_notification_manager.logger') as mock_logger:
            error = create_error(
                error_code="INTEGRATION_TEST_ERROR",
                message="Integration test error",
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.HIGH,
                context={"test": "integration"}
            )
            
            assert isinstance(error, AIAgentError)
            # Verify that error was logged (either error or warning level)
            assert mock_logger.error.called or mock_logger.warning.called
    
    def test_retry_with_performance_monitoring(self):
        """Test retry mechanism with performance monitoring."""
        call_count = 0
        
        @monitor_performance("retry_test_operation")
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        with patch('ai_agent.utils.performance_monitor.performance_monitor') as mock_monitor:
            mock_metrics = Mock()
            mock_monitor.start_operation.return_value = mock_metrics
            
            result = flaky_function()
            
            assert result == "success"
            assert call_count == 2
            mock_monitor.start_operation.assert_called_once()
            mock_monitor.finish_operation.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
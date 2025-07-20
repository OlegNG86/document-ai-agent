"""Centralized logging configuration and utilities."""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class CustomFormatter(logging.Formatter):
    """Custom formatter with colored output for console and structured logging."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True, include_extra: bool = False):
        """Initialize formatter.
        
        Args:
            use_colors: Whether to use colored output.
            include_extra: Whether to include extra fields in log records.
        """
        self.use_colors = use_colors
        self.include_extra = include_extra
        
        # Base format
        base_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        super().__init__(base_format)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and extra information."""
        # Add extra context if available
        if self.include_extra:
            extra_info = []
            
            # Add session ID if available
            if hasattr(record, 'session_id'):
                extra_info.append(f"session={record.session_id}")
            
            # Add document ID if available
            if hasattr(record, 'document_id'):
                extra_info.append(f"doc={record.document_id}")
            
            # Add processing time if available
            if hasattr(record, 'processing_time'):
                extra_info.append(f"time={record.processing_time:.2f}s")
            
            # Add operation type if available
            if hasattr(record, 'operation'):
                extra_info.append(f"op={record.operation}")
            
            if extra_info:
                record.msg = f"{record.msg} [{', '.join(extra_info)}]"
        
        # Format the base message
        formatted = super().format(record)
        
        # Add colors for console output
        if self.use_colors and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        extra_fields = ['session_id', 'document_id', 'processing_time', 'operation', 
                       'error_code', 'retry_count', 'user_id']
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        return json.dumps(log_entry, ensure_ascii=False)


class LoggingManager:
    """Centralized logging manager for the AI agent."""
    
    def __init__(self):
        """Initialize logging manager."""
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_dir = Path(os.getenv('LOG_DIR', 'logs'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.enable_file_logging = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'
        self.enable_json_logging = os.getenv('ENABLE_JSON_LOGGING', 'false').lower() == 'true'
        self.max_log_size = int(os.getenv('MAX_LOG_SIZE_MB', '10')) * 1024 * 1024  # Convert to bytes
        self.backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Create log directory
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup root logger
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """Setup root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level))
        console_formatter = CustomFormatter(use_colors=True, include_extra=True)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handlers
        if self.enable_file_logging:
            # Main log file
            main_log_file = self.log_dir / 'ai_agent.log'
            file_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, self.log_level))
            
            if self.enable_json_logging:
                file_formatter = JSONFormatter()
            else:
                file_formatter = CustomFormatter(use_colors=False, include_extra=True)
            
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            # Error log file (only ERROR and CRITICAL)
            error_log_file = self.log_dir / 'errors.log'
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            root_logger.addHandler(error_handler)
        
        # Reduce noise from external libraries
        self._configure_external_loggers()
    
    def _configure_external_loggers(self):
        """Configure logging levels for external libraries."""
        external_loggers = {
            'chromadb': logging.WARNING,
            'httpx': logging.WARNING,
            'urllib3': logging.WARNING,
            'requests': logging.WARNING,
            'ollama': logging.INFO
        }
        
        for logger_name, level in external_loggers.items():
            logging.getLogger(logger_name).setLevel(level)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the given name.
        
        Args:
            name: Logger name.
            
        Returns:
            Configured logger instance.
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_operation_start(self, logger: logging.Logger, operation: str, **kwargs):
        """Log the start of an operation with context.
        
        Args:
            logger: Logger instance.
            operation: Operation name.
            **kwargs: Additional context fields.
        """
        extra = {'operation': operation, **kwargs}
        logger.info(f"Starting {operation}", extra=extra)
    
    def log_operation_success(self, logger: logging.Logger, operation: str, 
                            processing_time: Optional[float] = None, **kwargs):
        """Log successful completion of an operation.
        
        Args:
            logger: Logger instance.
            operation: Operation name.
            processing_time: Time taken for the operation.
            **kwargs: Additional context fields.
        """
        extra = {'operation': operation, **kwargs}
        if processing_time is not None:
            extra['processing_time'] = processing_time
        
        message = f"Completed {operation}"
        if processing_time is not None:
            message += f" in {processing_time:.2f}s"
        
        logger.info(message, extra=extra)
    
    def log_operation_error(self, logger: logging.Logger, operation: str, error: Exception,
                          error_code: Optional[str] = None, **kwargs):
        """Log an error during an operation.
        
        Args:
            logger: Logger instance.
            operation: Operation name.
            error: Exception that occurred.
            error_code: Optional error code.
            **kwargs: Additional context fields.
        """
        extra = {'operation': operation, **kwargs}
        if error_code:
            extra['error_code'] = error_code
        
        # Add error classification
        extra['error_type'] = type(error).__name__
        extra['is_network_error'] = self._is_network_error(error)
        extra['is_temporary_error'] = self._is_temporary_error(error)
        
        logger.error(f"Error in {operation}: {error}", extra=extra, exc_info=True)
    
    def _is_network_error(self, error: Exception) -> bool:
        """Check if error is network-related."""
        from .error_handling import is_network_error
        return is_network_error(error)
    
    def _is_temporary_error(self, error: Exception) -> bool:
        """Check if error is temporary."""
        from .error_handling import is_temporary_error
        return is_temporary_error(error)
    
    def log_retry_attempt(self, logger: logging.Logger, operation: str, 
                         retry_count: int, max_retries: int, error: Exception, **kwargs):
        """Log a retry attempt.
        
        Args:
            logger: Logger instance.
            operation: Operation name.
            retry_count: Current retry count.
            max_retries: Maximum number of retries.
            error: Exception that caused the retry.
            **kwargs: Additional context fields.
        """
        extra = {'operation': operation, 'retry_count': retry_count, **kwargs}
        logger.warning(
            f"Retry {retry_count}/{max_retries} for {operation}: {error}",
            extra=extra
        )
    
    def create_operation_logger(self, base_logger: logging.Logger, **context) -> 'OperationLogger':
        """Create an operation logger with persistent context.
        
        Args:
            base_logger: Base logger to use.
            **context: Context fields to include in all log messages.
            
        Returns:
            OperationLogger instance.
        """
        return OperationLogger(base_logger, context)


class OperationLogger:
    """Logger wrapper that maintains operation context."""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any]):
        """Initialize operation logger.
        
        Args:
            logger: Base logger.
            context: Context to include in all messages.
        """
        self.logger = logger
        self.context = context
    
    def _log_with_context(self, level: int, message: str, **extra):
        """Log message with operation context.
        
        Args:
            level: Log level.
            message: Log message.
            **extra: Additional context.
        """
        combined_extra = {**self.context, **extra}
        self.logger.log(level, message, extra=combined_extra)
    
    def debug(self, message: str, **extra):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **extra)
    
    def info(self, message: str, **extra):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **extra)
    
    def warning(self, message: str, **extra):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **extra)
    
    def error(self, message: str, exc_info: bool = False, **extra):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **extra)
        if exc_info:
            self.logger.error(message, extra={**self.context, **extra}, exc_info=True)
    
    def critical(self, message: str, exc_info: bool = False, **extra):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **extra)
        if exc_info:
            self.logger.critical(message, extra={**self.context, **extra}, exc_info=True)


# Global logging manager instance
logging_manager = LoggingManager()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Configured logger.
    """
    return logging_manager.get_logger(name)


def setup_logging():
    """Setup logging configuration (for backward compatibility)."""
    # This function is kept for backward compatibility
    # The actual setup is done in LoggingManager.__init__
    pass
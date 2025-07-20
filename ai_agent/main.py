"""Main entry point for the AI agent application."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .cli.commands import cli
from .utils.logging_config import logging_manager, get_logger
from .utils.error_handling import handle_error, ErrorCategory, ErrorSeverity


logger = get_logger(__name__)


def setup_environment():
    """Setup environment variables and configuration."""
    # Load .env file if it exists
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
    
    # Set default environment variables if not set
    os.environ.setdefault('OLLAMA_HOST', 'http://localhost:11434')
    os.environ.setdefault('OLLAMA_DEFAULT_MODEL', 'llama3.1')
    os.environ.setdefault('DATA_PATH', 'data')
    os.environ.setdefault('DOCUMENTS_PATH', 'data/documents')
    os.environ.setdefault('CHROMA_PATH', 'data/chroma_db')
    
    # Create data directories if they don't exist
    data_path = Path(os.getenv('DATA_PATH'))
    documents_path = Path(os.getenv('DOCUMENTS_PATH'))
    chroma_path = Path(os.getenv('CHROMA_PATH'))
    
    for path in [data_path, documents_path, chroma_path]:
        path.mkdir(parents=True, exist_ok=True)


def main():
    """Main application entry point."""
    try:
        # Setup environment first
        setup_environment()
        
        # Logging is automatically configured by logging_manager
        logger.info("Starting AI Agent application")
        
        # Start CLI
        cli()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n👋 До свидания!")
        sys.exit(0)
    except Exception as e:
        # Handle critical startup errors
        error = handle_error(
            error=e,
            error_code="STARTUP_CRITICAL_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            suggestions=[
                "Check environment configuration",
                "Verify all dependencies are installed",
                "Check log files for detailed error information"
            ]
        )
        logger.critical(f"Critical startup error: {error.error_info.message}")
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
"""Main entry point for the AI agent application."""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

from .cli.commands import cli


def setup_logging():
    """Setup logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


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
        # Setup environment and logging
        setup_environment()
        setup_logging()
        
        # Start CLI
        cli()
        
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
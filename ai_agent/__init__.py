"""
AI Agent для работы с нормативной документацией по закупкам.
Использует Ollama для обработки естественного языка и ChromaDB для поиска по документам.
"""

__version__ = "0.1.0"
__author__ = "AI Assistant"

from .main import main

__all__ = ["main"]
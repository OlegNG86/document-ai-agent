"""Document model for the AI agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class Document:
    """Represents a document in the system."""
    
    id: str
    title: str
    content: str
    file_path: Path
    file_type: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[str] = field(default_factory=list)
    embedding_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate document data after initialization."""
        if not self.id:
            raise ValueError("Document ID cannot be empty")
        if not self.title:
            raise ValueError("Document title cannot be empty")
        if not self.content:
            raise ValueError("Document content cannot be empty")
        if not self.file_path:
            raise ValueError("Document file_path cannot be empty")
        if self.file_type not in ['txt', 'md']:
            raise ValueError("Document file_type must be 'txt' or 'md'")
    
    def add_chunk(self, chunk: str, embedding_id: Optional[str] = None) -> None:
        """Add a text chunk to the document."""
        self.chunks.append(chunk)
        if embedding_id:
            self.embedding_ids.append(embedding_id)
        self.updated_at = datetime.now()
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update document metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_summary(self) -> str:
        """Get a brief summary of the document."""
        return f"Document '{self.title}' ({self.file_type}) - {len(self.chunks)} chunks"
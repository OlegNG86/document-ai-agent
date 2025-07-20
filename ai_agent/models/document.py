"""Document model for the AI agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum


class DocumentCategory(Enum):
    """Document category enumeration."""
    REFERENCE = "reference"  # Reference/normative documents
    TARGET = "target"       # Target documents for checking
    GENERAL = "general"     # General documents (default)


@dataclass
class Document:
    """Represents a document in the system."""
    
    id: str
    title: str
    content: str
    file_path: Path
    file_type: str
    category: DocumentCategory = DocumentCategory.GENERAL
    tags: List[str] = field(default_factory=list)
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
        if self.file_type not in ['txt', 'md', 'docx', 'pdf', 'rtf']:
            raise ValueError("Document file_type must be 'txt', 'md', 'docx', 'pdf', or 'rtf'")
        if isinstance(self.category, str):
            # Convert string to enum if needed
            self.category = DocumentCategory(self.category)
    
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
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the document."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the document."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def set_category(self, category: DocumentCategory) -> None:
        """Set document category."""
        self.category = category
        self.updated_at = datetime.now()
    
    def is_reference_document(self) -> bool:
        """Check if document is a reference/normative document."""
        return self.category == DocumentCategory.REFERENCE
    
    def is_target_document(self) -> bool:
        """Check if document is a target document for checking."""
        return self.category == DocumentCategory.TARGET
    
    def get_summary(self) -> str:
        """Get a brief summary of the document."""
        category_str = self.category.value if self.category else "general"
        tags_str = f" [{', '.join(self.tags)}]" if self.tags else ""
        return f"Document '{self.title}' ({self.file_type}, {category_str}){tags_str} - {len(self.chunks)} chunks"
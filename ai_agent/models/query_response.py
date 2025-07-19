"""Query response model for the AI agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class QueryResponse:
    """Represents a response to a user query."""
    
    id: str
    query: str
    response: str
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    processing_time: Optional[float] = None
    relevant_documents: List[str] = field(default_factory=list)
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate query response data after initialization."""
        if not self.id:
            raise ValueError("QueryResponse ID cannot be empty")
        if not self.query:
            raise ValueError("QueryResponse query cannot be empty")
        if not self.response:
            raise ValueError("QueryResponse response cannot be empty")
        if not self.session_id:
            raise ValueError("QueryResponse session_id cannot be empty")
        if self.confidence_score is not None:
            if not 0.0 <= self.confidence_score <= 1.0:
                raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.processing_time is not None and self.processing_time < 0:
            raise ValueError("Processing time cannot be negative")
    
    def add_relevant_document(self, document_id: str) -> None:
        """Add a relevant document to the response."""
        if document_id not in self.relevant_documents:
            self.relevant_documents.append(document_id)
    
    def set_confidence_score(self, score: float) -> None:
        """Set the confidence score for the response."""
        if not 0.0 <= score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        self.confidence_score = score
    
    def set_processing_time(self, time_seconds: float) -> None:
        """Set the processing time for the response."""
        if time_seconds < 0:
            raise ValueError("Processing time cannot be negative")
        self.processing_time = time_seconds
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update response metadata."""
        self.metadata[key] = value
    
    def get_summary(self) -> str:
        """Get a brief summary of the query response."""
        query_preview = self.query[:30] + "..." if len(self.query) > 30 else self.query
        response_preview = self.response[:50] + "..." if len(self.response) > 50 else self.response
        return f"Query: '{query_preview}' -> Response: '{response_preview}'"
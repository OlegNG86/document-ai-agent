"""Session model for the AI agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from .message import Message


@dataclass
class Session:
    """Represents a user session with the AI agent."""
    
    id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def __post_init__(self):
        """Validate session data after initialization."""
        if not self.id:
            raise ValueError("Session ID cannot be empty")
    
    def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get the most recent messages from the session."""
        return self.messages[-limit:] if self.messages else []
    
    def get_message_count(self) -> int:
        """Get the total number of messages in the session."""
        return len(self.messages)
    
    def clear_messages(self) -> None:
        """Clear all messages from the session."""
        self.messages.clear()
        self.updated_at = datetime.now()
    
    def deactivate(self) -> None:
        """Deactivate the session."""
        self.is_active = False
        self.updated_at = datetime.now()
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update session metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_summary(self) -> str:
        """Get a brief summary of the session."""
        status = "active" if self.is_active else "inactive"
        return f"Session {self.id} ({status}) - {self.get_message_count()} messages"
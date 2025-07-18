"""Message model for the AI agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class MessageType(Enum):
    """Types of messages in the system."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a message in a conversation."""
    
    id: str
    content: str
    message_type: MessageType
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_message_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate message data after initialization."""
        if not self.id:
            raise ValueError("Message ID cannot be empty")
        if not self.content:
            raise ValueError("Message content cannot be empty")
        if not self.session_id:
            raise ValueError("Message session_id cannot be empty")
        if not isinstance(self.message_type, MessageType):
            raise ValueError("Message type must be a MessageType enum")
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update message metadata."""
        self.metadata[key] = value
    
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.message_type == MessageType.USER
    
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.message_type == MessageType.ASSISTANT
    
    def is_system_message(self) -> bool:
        """Check if this is a system message."""
        return self.message_type == MessageType.SYSTEM
    
    def get_summary(self) -> str:
        """Get a brief summary of the message."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.message_type.value}: {content_preview}"
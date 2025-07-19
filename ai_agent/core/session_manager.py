"""Session manager for handling user sessions and conversation history."""

import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from threading import Lock

from ..models.session import Session
from ..models.message import Message, MessageType


logger = logging.getLogger(__name__)


class SessionManagerError(Exception):
    """Exception raised for session management errors."""
    pass


class SessionManager:
    """Manages user sessions and conversation history in memory."""
    
    def __init__(self, session_timeout_hours: int = 24):
        """Initialize session manager.
        
        Args:
            session_timeout_hours: Hours after which inactive sessions expire.
        """
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self._lock = Lock()  # Thread safety for concurrent access
        
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new session.
        
        Args:
            user_id: Optional user identifier.
            
        Returns:
            Session ID.
        """
        with self._lock:
            session_id = str(uuid.uuid4())
            
            session = Session(
                id=session_id,
                user_id=user_id
            )
            
            self.sessions[session_id] = session
            
            logger.info(f"Created new session: {session_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Session object or None if not found.
        """
        with self._lock:
            session = self.sessions.get(session_id)
            
            if session and self._is_session_expired(session):
                self._cleanup_session(session_id)
                return None
                
            return session
    
    def get_session_history(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get conversation history for a session.
        
        Args:
            session_id: Session identifier.
            limit: Maximum number of messages to return. If None, returns all.
            
        Returns:
            List of messages in chronological order.
            
        Raises:
            SessionManagerError: If session not found.
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionManagerError(f"Session not found: {session_id}")
        
        if limit is None:
            return session.messages.copy()
        
        return session.get_recent_messages(limit)
    
    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to a session.
        
        Args:
            session_id: Session identifier.
            message: Message to add.
            
        Raises:
            SessionManagerError: If session not found.
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionManagerError(f"Session not found: {session_id}")
        
        with self._lock:
            session.add_message(message)
            logger.debug(f"Added message to session {session_id}: {message.get_summary()}")
    
    def add_user_message(self, session_id: str, content: str, metadata: Optional[Dict] = None) -> str:
        """Add a user message to a session.
        
        Args:
            session_id: Session identifier.
            content: Message content.
            metadata: Optional message metadata.
            
        Returns:
            Message ID.
            
        Raises:
            SessionManagerError: If session not found.
        """
        message_id = str(uuid.uuid4())
        
        message = Message(
            id=message_id,
            content=content,
            message_type=MessageType.USER,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.add_message(session_id, message)
        return message_id
    
    def add_assistant_message(
        self, 
        session_id: str, 
        content: str, 
        metadata: Optional[Dict] = None,
        parent_message_id: Optional[str] = None
    ) -> str:
        """Add an assistant message to a session.
        
        Args:
            session_id: Session identifier.
            content: Message content.
            metadata: Optional message metadata.
            parent_message_id: ID of the message this is responding to.
            
        Returns:
            Message ID.
            
        Raises:
            SessionManagerError: If session not found.
        """
        message_id = str(uuid.uuid4())
        
        message = Message(
            id=message_id,
            content=content,
            message_type=MessageType.ASSISTANT,
            session_id=session_id,
            metadata=metadata or {},
            parent_message_id=parent_message_id
        )
        
        self.add_message(session_id, message)
        return message_id
    
    def clear_session(self, session_id: str) -> bool:
        """Clear messages from a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            True if cleared successfully, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        with self._lock:
            session.clear_messages()
            logger.info(f"Cleared session: {session_id}")
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session completely.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            True if deleted successfully, False if session not found.
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """List all active sessions.
        
        Args:
            user_id: Filter sessions by user ID. If None, returns all sessions.
            
        Returns:
            List of session information dicts.
        """
        with self._lock:
            # Clean up expired sessions first
            self._cleanup_expired_sessions()
            
            sessions_info = []
            for session in self.sessions.values():
                if user_id is None or session.user_id == user_id:
                    sessions_info.append({
                        'id': session.id,
                        'user_id': session.user_id,
                        'created_at': session.created_at.isoformat(),
                        'updated_at': session.updated_at.isoformat(),
                        'message_count': session.get_message_count(),
                        'is_active': session.is_active
                    })
            
            return sessions_info
    
    def get_session_stats(self) -> Dict:
        """Get statistics about all sessions.
        
        Returns:
            Dictionary with session statistics.
        """
        with self._lock:
            self._cleanup_expired_sessions()
            
            total_sessions = len(self.sessions)
            total_messages = sum(session.get_message_count() for session in self.sessions.values())
            active_sessions = sum(1 for session in self.sessions.values() if session.is_active)
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'total_messages': total_messages,
                'average_messages_per_session': total_messages / total_sessions if total_sessions > 0 else 0
            }
    
    def update_session_metadata(self, session_id: str, key: str, value) -> bool:
        """Update session metadata.
        
        Args:
            session_id: Session identifier.
            key: Metadata key.
            value: Metadata value.
            
        Returns:
            True if updated successfully, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        with self._lock:
            session.update_metadata(key, value)
            return True
    
    def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session without deleting it.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            True if deactivated successfully, False if session not found.
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        with self._lock:
            session.deactivate()
            logger.info(f"Deactivated session: {session_id}")
            return True
    
    def _is_session_expired(self, session: Session) -> bool:
        """Check if a session has expired.
        
        Args:
            session: Session to check.
            
        Returns:
            True if session has expired, False otherwise.
        """
        return datetime.now() - session.updated_at > self.session_timeout
    
    def _cleanup_session(self, session_id: str) -> None:
        """Clean up a single session.
        
        Args:
            session_id: Session to clean up.
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up all expired sessions."""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self._cleanup_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def cleanup_all_sessions(self) -> int:
        """Clean up all sessions (useful for shutdown).
        
        Returns:
            Number of sessions cleaned up.
        """
        with self._lock:
            count = len(self.sessions)
            self.sessions.clear()
            logger.info(f"Cleaned up all {count} sessions")
            return count
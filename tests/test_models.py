"""Unit tests for the AI agent models."""

import pytest
from datetime import datetime
from pathlib import Path

from ai_agent.models.document import Document
from ai_agent.models.session import Session
from ai_agent.models.message import Message, MessageType
from ai_agent.models.query_response import QueryResponse


class TestDocument:
    """Test cases for the Document model."""
    
    def test_document_creation_valid(self):
        """Test creating a valid document."""
        doc = Document(
            id="doc1",
            title="Test Document",
            content="This is test content",
            file_path=Path("/test/file.txt"),
            file_type="txt"
        )
        assert doc.id == "doc1"
        assert doc.title == "Test Document"
        assert doc.content == "This is test content"
        assert doc.file_type == "txt"
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)
        assert doc.chunks == []
        assert doc.metadata == {}
    
    def test_document_validation_empty_id(self):
        """Test document validation with empty ID."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            Document(
                id="",
                title="Test",
                content="Content",
                file_path=Path("/test/file.txt"),
                file_type="txt"
            )
    
    def test_document_validation_invalid_file_type(self):
        """Test document validation with invalid file type."""
        with pytest.raises(ValueError, match="Document file_type must be 'txt', 'md', or 'docx'"):
            Document(
                id="doc1",
                title="Test",
                content="Content",
                file_path=Path("/test/file.pdf"),
                file_type="pdf"
            )
    
    def test_document_add_chunk(self):
        """Test adding chunks to document."""
        doc = Document(
            id="doc1",
            title="Test",
            content="Content",
            file_path=Path("/test/file.txt"),
            file_type="txt"
        )
        doc.add_chunk("Chunk 1", "embed1")
        assert len(doc.chunks) == 1
        assert doc.chunks[0] == "Chunk 1"
        assert len(doc.embedding_ids) == 1
        assert doc.embedding_ids[0] == "embed1"


class TestSession:
    """Test cases for the Session model."""
    
    def test_session_creation_valid(self):
        """Test creating a valid session."""
        session = Session(id="session1", user_id="user1")
        assert session.id == "session1"
        assert session.user_id == "user1"
        assert session.is_active is True
        assert session.messages == []
        assert isinstance(session.created_at, datetime)
    
    def test_session_validation_empty_id(self):
        """Test session validation with empty ID."""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            Session(id="")
    
    def test_session_add_message(self):
        """Test adding message to session."""
        session = Session(id="session1")
        message = Message(
            id="msg1",
            content="Hello",
            message_type=MessageType.USER,
            session_id="session1"
        )
        session.add_message(message)
        assert len(session.messages) == 1
        assert session.messages[0] == message
    
    def test_session_get_recent_messages(self):
        """Test getting recent messages from session."""
        session = Session(id="session1")
        for i in range(15):
            message = Message(
                id=f"msg{i}",
                content=f"Message {i}",
                message_type=MessageType.USER,
                session_id="session1"
            )
            session.add_message(message)
        
        recent = session.get_recent_messages(5)
        assert len(recent) == 5
        assert recent[0].content == "Message 10"
        assert recent[-1].content == "Message 14"


class TestMessage:
    """Test cases for the Message model."""
    
    def test_message_creation_valid(self):
        """Test creating a valid message."""
        message = Message(
            id="msg1",
            content="Hello world",
            message_type=MessageType.USER,
            session_id="session1"
        )
        assert message.id == "msg1"
        assert message.content == "Hello world"
        assert message.message_type == MessageType.USER
        assert message.session_id == "session1"
        assert isinstance(message.created_at, datetime)
    
    def test_message_validation_empty_content(self):
        """Test message validation with empty content."""
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            Message(
                id="msg1",
                content="",
                message_type=MessageType.USER,
                session_id="session1"
            )
    
    def test_message_type_checks(self):
        """Test message type checking methods."""
        user_msg = Message(
            id="msg1",
            content="Hello",
            message_type=MessageType.USER,
            session_id="session1"
        )
        assert user_msg.is_user_message() is True
        assert user_msg.is_assistant_message() is False
        assert user_msg.is_system_message() is False
        
        assistant_msg = Message(
            id="msg2",
            content="Hi there",
            message_type=MessageType.ASSISTANT,
            session_id="session1"
        )
        assert assistant_msg.is_assistant_message() is True
        assert assistant_msg.is_user_message() is False


class TestQueryResponse:
    """Test cases for the QueryResponse model."""
    
    def test_query_response_creation_valid(self):
        """Test creating a valid query response."""
        response = QueryResponse(
            id="resp1",
            query="What is AI?",
            response="AI is artificial intelligence",
            session_id="session1"
        )
        assert response.id == "resp1"
        assert response.query == "What is AI?"
        assert response.response == "AI is artificial intelligence"
        assert response.session_id == "session1"
        assert isinstance(response.created_at, datetime)
        assert response.relevant_documents == []
    
    def test_query_response_validation_empty_query(self):
        """Test query response validation with empty query."""
        with pytest.raises(ValueError, match="QueryResponse query cannot be empty"):
            QueryResponse(
                id="resp1",
                query="",
                response="Response",
                session_id="session1"
            )
    
    def test_query_response_confidence_score_validation(self):
        """Test confidence score validation."""
        response = QueryResponse(
            id="resp1",
            query="Test",
            response="Response",
            session_id="session1"
        )
        
        # Valid confidence score
        response.set_confidence_score(0.85)
        assert response.confidence_score == 0.85
        
        # Invalid confidence score
        with pytest.raises(ValueError, match="Confidence score must be between 0.0 and 1.0"):
            response.set_confidence_score(1.5)
    
    def test_query_response_add_relevant_document(self):
        """Test adding relevant documents."""
        response = QueryResponse(
            id="resp1",
            query="Test",
            response="Response",
            session_id="session1"
        )
        
        response.add_relevant_document("doc1")
        response.add_relevant_document("doc2")
        response.add_relevant_document("doc1")  # Duplicate should not be added
        
        assert len(response.relevant_documents) == 2
        assert "doc1" in response.relevant_documents
        assert "doc2" in response.relevant_documents
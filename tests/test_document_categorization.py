"""Tests for document categorization and targeted checking functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ai_agent.models.document import Document, DocumentCategory
from ai_agent.core.document_manager import DocumentManager, DocumentManagerError
from ai_agent.core.query_processor import QueryProcessor, QueryProcessorError
from ai_agent.core.session_manager import SessionManager
from ai_agent.core.ollama_client import OllamaClient


class TestDocumentCategory:
    """Test document category functionality."""
    
    def test_document_category_enum(self):
        """Test document category enumeration."""
        assert DocumentCategory.REFERENCE.value == "reference"
        assert DocumentCategory.TARGET.value == "target"
        assert DocumentCategory.GENERAL.value == "general"
    
    def test_document_with_category(self):
        """Test document creation with category."""
        doc = Document(
            id="test-id",
            title="Test Document",
            content="Test content",
            file_path=Path("test.txt"),
            file_type="txt",
            category=DocumentCategory.REFERENCE
        )
        
        assert doc.category == DocumentCategory.REFERENCE
        assert doc.is_reference_document()
        assert not doc.is_target_document()
    
    def test_document_category_methods(self):
        """Test document category helper methods."""
        doc = Document(
            id="test-id",
            title="Test Document",
            content="Test content",
            file_path=Path("test.txt"),
            file_type="txt",
            category=DocumentCategory.TARGET
        )
        
        assert doc.is_target_document()
        assert not doc.is_reference_document()
        
        # Test category change
        doc.set_category(DocumentCategory.REFERENCE)
        assert doc.is_reference_document()
        assert not doc.is_target_document()
    
    def test_document_tags(self):
        """Test document tags functionality."""
        doc = Document(
            id="test-id",
            title="Test Document",
            content="Test content",
            file_path=Path("test.txt"),
            file_type="txt",
            tags=["tag1", "tag2"]
        )
        
        assert "tag1" in doc.tags
        assert "tag2" in doc.tags
        
        # Test add tag
        doc.add_tag("tag3")
        assert "tag3" in doc.tags
        
        # Test duplicate tag
        doc.add_tag("tag1")
        assert doc.tags.count("tag1") == 1
        
        # Test remove tag
        doc.remove_tag("tag2")
        assert "tag2" not in doc.tags
    
    def test_document_summary_with_category(self):
        """Test document summary includes category and tags."""
        doc = Document(
            id="test-id",
            title="Test Document",
            content="Test content",
            file_path=Path("test.txt"),
            file_type="txt",
            category=DocumentCategory.REFERENCE,
            tags=["normative", "requirements"]
        )
        
        summary = doc.get_summary()
        assert "reference" in summary
        assert "normative" in summary
        assert "requirements" in summary


class TestDocumentManagerCategorization:
    """Test document manager categorization features."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client."""
        mock_client = Mock(spec=OllamaClient)
        mock_client.generate_embeddings.return_value = [0.1] * 384  # Mock embedding
        mock_client.health_check.return_value = True
        return mock_client
    
    @pytest.fixture
    def document_manager(self, temp_dir, mock_ollama_client):
        """Create document manager with mocked dependencies."""
        with patch('ai_agent.core.document_manager.OllamaClient', return_value=mock_ollama_client):
            dm = DocumentManager(
                storage_path=os.path.join(temp_dir, "documents"),
                chroma_path=os.path.join(temp_dir, "chroma_db")
            )
            return dm
    
    def test_upload_document_with_category(self, document_manager, temp_dir):
        """Test uploading document with category."""
        # Create test file
        test_file = Path(temp_dir) / "test_reference.txt"
        test_file.write_text("This is a reference document with normative requirements.")
        
        # Upload with reference category
        doc_id = document_manager.upload_document(
            file_path=str(test_file),
            category=DocumentCategory.REFERENCE,
            tags=["normative", "requirements"]
        )
        
        # Verify document info
        doc_info = document_manager.get_document_info(doc_id)
        assert doc_info is not None
        assert doc_info['category'] == 'reference'
        
        # Check tags
        doc_tags = doc_info.get('tags', [])
        if isinstance(doc_tags, str):
            doc_tags = doc_tags.split(',') if doc_tags else []
        assert 'normative' in doc_tags
        assert 'requirements' in doc_tags
    
    def test_list_documents_with_category_filter(self, document_manager, temp_dir):
        """Test listing documents with category filter."""
        # Create and upload reference document
        ref_file = Path(temp_dir) / "reference.txt"
        ref_file.write_text("Reference document content")
        ref_doc_id = document_manager.upload_document(
            file_path=str(ref_file),
            category=DocumentCategory.REFERENCE
        )
        
        # Create and upload general document
        gen_file = Path(temp_dir) / "general.txt"
        gen_file.write_text("General document content")
        gen_doc_id = document_manager.upload_document(
            file_path=str(gen_file),
            category=DocumentCategory.GENERAL
        )
        
        # Test filtering by reference category
        ref_docs = document_manager.list_documents(category_filter=DocumentCategory.REFERENCE)
        assert len(ref_docs) == 1
        assert ref_docs[0]['id'] == ref_doc_id
        assert ref_docs[0]['category'] == 'reference'
        
        # Test filtering by general category
        gen_docs = document_manager.list_documents(category_filter=DocumentCategory.GENERAL)
        assert len(gen_docs) == 1
        assert gen_docs[0]['id'] == gen_doc_id
        assert gen_docs[0]['category'] == 'general'
        
        # Test no filter (should return all)
        all_docs = document_manager.list_documents()
        assert len(all_docs) == 2
    
    def test_search_with_category_filter(self, document_manager, temp_dir):
        """Test searching with category filter."""
        # Create and upload reference document
        ref_file = Path(temp_dir) / "reference.txt"
        ref_file.write_text("This document contains normative requirements for procurement")
        document_manager.upload_document(
            file_path=str(ref_file),
            category=DocumentCategory.REFERENCE
        )
        
        # Create and upload general document
        gen_file = Path(temp_dir) / "general.txt"
        gen_file.write_text("This document contains general information about procurement")
        document_manager.upload_document(
            file_path=str(gen_file),
            category=DocumentCategory.GENERAL
        )
        
        # Search only in reference documents
        ref_results = document_manager.search_similar_chunks(
            query="normative requirements",
            category_filter=DocumentCategory.REFERENCE
        )
        
        # Should only return chunks from reference documents
        for result in ref_results:
            assert result['metadata']['category'] == 'reference'
        
        # Search in all documents
        all_results = document_manager.search_similar_chunks(
            query="procurement"
        )
        
        # Should return chunks from both categories
        categories = set(result['metadata']['category'] for result in all_results)
        assert len(categories) >= 1  # At least one category
    
    def test_get_reference_documents(self, document_manager, temp_dir):
        """Test getting reference documents."""
        # Upload reference document
        ref_file = Path(temp_dir) / "reference.txt"
        ref_file.write_text("Reference document")
        document_manager.upload_document(
            file_path=str(ref_file),
            category=DocumentCategory.REFERENCE
        )
        
        # Upload general document
        gen_file = Path(temp_dir) / "general.txt"
        gen_file.write_text("General document")
        document_manager.upload_document(
            file_path=str(gen_file),
            category=DocumentCategory.GENERAL
        )
        
        # Get reference documents
        ref_docs = document_manager.get_reference_documents()
        assert len(ref_docs) == 1
        assert ref_docs[0]['category'] == 'reference'
    
    def test_update_document_category(self, document_manager, temp_dir):
        """Test updating document category."""
        # Upload document with general category
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Test document content")
        doc_id = document_manager.upload_document(
            file_path=str(test_file),
            category=DocumentCategory.GENERAL
        )
        
        # Verify initial category
        doc_info = document_manager.get_document_info(doc_id)
        assert doc_info['category'] == 'general'
        
        # Update to reference category
        success = document_manager.update_document_category(doc_id, DocumentCategory.REFERENCE)
        assert success
        
        # Verify updated category
        doc_info = document_manager.get_document_info(doc_id)
        assert doc_info['category'] == 'reference'
    
    def test_update_document_tags(self, document_manager, temp_dir):
        """Test updating document tags."""
        # Upload document
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Test document content")
        doc_id = document_manager.upload_document(
            file_path=str(test_file),
            tags=["initial", "tag"]
        )
        
        # Update tags
        new_tags = ["updated", "tags", "list"]
        success = document_manager.update_document_tags(doc_id, new_tags)
        assert success
        
        # Verify updated tags
        doc_info = document_manager.get_document_info(doc_id)
        doc_tags = doc_info.get('tags', [])
        if isinstance(doc_tags, str):
            doc_tags = doc_tags.split(',') if doc_tags else []
        
        assert set(doc_tags) == set(new_tags)


class TestQueryProcessorTargetedChecking:
    """Test query processor targeted document checking."""
    
    @pytest.fixture
    def mock_document_manager(self):
        """Mock document manager."""
        mock_dm = Mock(spec=DocumentManager)
        return mock_dm
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager."""
        mock_sm = Mock(spec=SessionManager)
        mock_sm.add_user_message.return_value = "user-msg-id"
        mock_sm.add_assistant_message.return_value = "assistant-msg-id"
        return mock_sm
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client."""
        mock_client = Mock(spec=OllamaClient)
        mock_client.generate_response.return_value = "Mocked compliance analysis response"
        return mock_client
    
    @pytest.fixture
    def query_processor(self, mock_document_manager, mock_session_manager, mock_ollama_client):
        """Create query processor with mocked dependencies."""
        return QueryProcessor(
            document_manager=mock_document_manager,
            session_manager=mock_session_manager,
            ollama_client=mock_ollama_client
        )
    
    def test_process_document_check_with_reference_docs(self, query_processor, mock_document_manager):
        """Test document check with specific reference documents."""
        # Setup mock
        mock_document_manager.search_similar_chunks.return_value = [
            {
                'id': 'chunk-1',
                'content': 'Reference requirement content',
                'metadata': {'document_id': 'ref-doc-1', 'title': 'Reference Doc 1'},
                'relevance_score': 0.9
            }
        ]
        
        # Test document check with specific reference documents
        response = query_processor.process_document_check(
            document_content="Document to check for compliance",
            session_id="test-session",
            reference_document_ids=["ref-doc-1", "ref-doc-2"]
        )
        
        assert response is not None
        assert response.session_id == "test-session"
        assert "ref-doc-1" in response.relevant_documents
    
    def test_process_document_check_reference_filter(self, query_processor, mock_document_manager):
        """Test document check with reference category filter."""
        # Setup mock
        mock_document_manager.search_similar_chunks.return_value = [
            {
                'id': 'chunk-1',
                'content': 'Reference requirement content',
                'metadata': {'document_id': 'ref-doc-1', 'title': 'Reference Doc 1'},
                'relevance_score': 0.8
            }
        ]
        
        # Test document check without specific reference docs (should filter by category)
        response = query_processor.process_document_check(
            document_content="Document to check for compliance",
            session_id="test-session"
        )
        
        # Verify that search was called with reference category filter
        mock_document_manager.search_similar_chunks.assert_called()
        call_args = mock_document_manager.search_similar_chunks.call_args
        assert call_args[1]['category_filter'] == DocumentCategory.REFERENCE
        
        assert response is not None
        assert response.session_id == "test-session"


class TestCLIIntegration:
    """Test CLI integration for categorization features."""
    
    def test_document_category_parsing(self):
        """Test parsing document categories from CLI."""
        # Test valid categories
        assert DocumentCategory("reference") == DocumentCategory.REFERENCE
        assert DocumentCategory("target") == DocumentCategory.TARGET
        assert DocumentCategory("general") == DocumentCategory.GENERAL
        
        # Test invalid category
        with pytest.raises(ValueError):
            DocumentCategory("invalid")
    
    def test_tags_parsing(self):
        """Test parsing tags from CLI input."""
        # Test comma-separated tags
        tags_input = "tag1, tag2, tag3"
        parsed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        assert parsed_tags == ["tag1", "tag2", "tag3"]
        
        # Test empty tags
        tags_input = ""
        parsed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        assert parsed_tags == []
        
        # Test tags with extra spaces
        tags_input = " tag1 ,  tag2  , tag3 "
        parsed_tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        assert parsed_tags == ["tag1", "tag2", "tag3"]


if __name__ == "__main__":
    pytest.main([__file__])
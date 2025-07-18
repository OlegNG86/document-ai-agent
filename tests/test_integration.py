"""Integration tests for the AI agent."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from ai_agent.core.document_manager import DocumentManager, DocumentManagerError
from ai_agent.core.session_manager import SessionManager
from ai_agent.core.query_processor import QueryProcessor
from ai_agent.core.ollama_client import OllamaClient
from ai_agent.models.message import MessageType


class TestDocumentManagerIntegration:
    """Integration tests for document management."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "documents"
            chroma_path = Path(temp_dir) / "chroma_db"
            yield storage_path, chroma_path
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client for testing."""
        mock_client = Mock(spec=OllamaClient)
        mock_client.generate_embeddings.return_value = [0.1] * 384  # Mock embedding
        return mock_client
    
    @pytest.fixture
    def document_manager(self, temp_dirs, mock_ollama_client):
        """Create document manager with mocked dependencies."""
        storage_path, chroma_path = temp_dirs
        
        with patch('ai_agent.core.document_manager.OllamaClient', return_value=mock_ollama_client):
            dm = DocumentManager(
                storage_path=str(storage_path),
                chroma_path=str(chroma_path),
                chunk_size=100,
                chunk_overlap=20
            )
            return dm
    
    def test_document_upload_and_search_workflow(self, document_manager, temp_dirs):
        """Test complete document upload and search workflow."""
        storage_path, _ = temp_dirs
        
        # Create test document
        test_file = storage_path.parent / "test_doc.txt"
        test_content = """
        Это тестовый документ по нормативам закупок.
        В документе описаны требования к поставщикам.
        Поставщик должен соответствовать следующим критериям:
        1. Наличие лицензии
        2. Опыт работы не менее 3 лет
        3. Положительные отзывы клиентов
        """
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Upload document
        doc_id = document_manager.upload_document(
            file_path=str(test_file),
            metadata={'category': 'normative', 'version': '1.0'}
        )
        
        assert doc_id is not None
        assert len(doc_id) > 0
        
        # Verify document info
        doc_info = document_manager.get_document_info(doc_id)
        assert doc_info is not None
        assert doc_info['title'] == 'test_doc'
        assert doc_info['file_type'] == 'txt'
        assert doc_info['chunk_count'] > 0
        
        # Search for similar content
        search_results = document_manager.search_similar_chunks(
            "требования к поставщикам", top_k=3
        )
        
        assert len(search_results) > 0
        assert any("поставщик" in result['content'].lower() for result in search_results)
        
        # List documents
        documents = document_manager.list_documents()
        assert len(documents) == 1
        assert documents[0]['id'] == doc_id
        
        # Delete document
        assert document_manager.delete_document(doc_id) is True
        
        # Verify deletion
        assert document_manager.get_document_info(doc_id) is None
        assert len(document_manager.list_documents()) == 0


class TestSessionManagerIntegration:
    """Integration tests for session management."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing."""
        return SessionManager(session_timeout_hours=1)
    
    def test_session_lifecycle(self, session_manager):
        """Test complete session lifecycle."""
        # Create session
        session_id = session_manager.create_session(user_id="test_user")
        assert session_id is not None
        
        # Get session
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.id == session_id
        assert session.user_id == "test_user"
        assert session.is_active is True
        
        # Add messages
        user_msg_id = session_manager.add_user_message(
            session_id, "Какие требования к поставщикам?"
        )
        assert user_msg_id is not None
        
        assistant_msg_id = session_manager.add_assistant_message(
            session_id, 
            "Требования включают наличие лицензии и опыт работы.",
            parent_message_id=user_msg_id
        )
        assert assistant_msg_id is not None
        
        # Get history
        history = session_manager.get_session_history(session_id)
        assert len(history) == 2
        assert history[0].message_type == MessageType.USER
        assert history[1].message_type == MessageType.ASSISTANT
        assert history[1].parent_message_id == user_msg_id
        
        # List sessions
        sessions = session_manager.list_sessions(user_id="test_user")
        assert len(sessions) == 1
        assert sessions[0]['id'] == session_id
        
        # Get stats
        stats = session_manager.get_session_stats()
        assert stats['total_sessions'] == 1
        assert stats['active_sessions'] == 1
        assert stats['total_messages'] == 2
        
        # Clear session
        assert session_manager.clear_session(session_id) is True
        history = session_manager.get_session_history(session_id)
        assert len(history) == 0
        
        # Delete session
        assert session_manager.delete_session(session_id) is True
        assert session_manager.get_session(session_id) is None


class TestQueryProcessorIntegration:
    """Integration tests for query processing."""
    
    @pytest.fixture
    def mock_components(self, temp_dirs):
        """Create mocked components for testing."""
        storage_path, chroma_path = temp_dirs
        
        # Mock Ollama client
        mock_ollama = Mock(spec=OllamaClient)
        mock_ollama.generate_embeddings.return_value = [0.1] * 384
        mock_ollama.generate_response.return_value = "Это ответ от AI модели на ваш запрос."
        
        # Create real document manager with mocked Ollama
        with patch('ai_agent.core.document_manager.OllamaClient', return_value=mock_ollama):
            doc_manager = DocumentManager(
                storage_path=str(storage_path),
                chroma_path=str(chroma_path)
            )
        
        # Create session manager
        session_manager = SessionManager()
        
        return doc_manager, session_manager, mock_ollama
    
    @pytest.fixture
    def query_processor(self, mock_components):
        """Create query processor with mocked dependencies."""
        doc_manager, session_manager, mock_ollama = mock_components
        return QueryProcessor(doc_manager, session_manager, mock_ollama)
    
    def test_general_query_processing(self, query_processor, mock_components):
        """Test general query processing workflow."""
        doc_manager, session_manager, mock_ollama = mock_components
        
        # Create session
        session_id = session_manager.create_session()
        
        # Add test document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Документ содержит информацию о требованиях к закупкам.")
            test_file = f.name
        
        try:
            doc_manager.upload_document(test_file)
            
            # Process query
            response = query_processor.process_general_query(
                "Какие требования к закупкам?", 
                session_id
            )
            
            assert response is not None
            assert response.query == "Какие требования к закупкам?"
            assert len(response.response) > 0
            assert response.session_id == session_id
            assert response.processing_time is not None
            assert response.processing_time > 0
            
            # Verify session history was updated
            history = session_manager.get_session_history(session_id)
            assert len(history) == 2  # User message + assistant response
            assert history[0].is_user_message()
            assert history[1].is_assistant_message()
            
            # Verify Ollama was called
            mock_ollama.generate_response.assert_called_once()
            
        finally:
            os.unlink(test_file)
    
    def test_document_check_processing(self, query_processor, mock_components):
        """Test document compliance check workflow."""
        doc_manager, session_manager, mock_ollama = mock_components
        
        # Create session
        session_id = session_manager.create_session()
        
        # Add normative document
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("""
            Нормативные требования к договорам:
            1. Указание срока поставки
            2. Указание цены и условий оплаты
            3. Подписи сторон
            """)
            normative_file = f.name
        
        try:
            doc_manager.upload_document(normative_file)
            
            # Document to check
            document_content = """
            Договор поставки товаров
            Срок поставки: 30 дней
            Цена: 100000 рублей
            """
            
            # Process document check
            response = query_processor.process_document_check(
                document_content, 
                session_id
            )
            
            assert response is not None
            assert response.query == "Проверка документа на соответствие"
            assert len(response.response) > 0
            assert response.session_id == session_id
            
            # Verify session history
            history = session_manager.get_session_history(session_id)
            assert len(history) == 2
            
            # Check metadata
            assistant_message = history[1]
            assert assistant_message.metadata.get('check_type') == 'document_compliance'
            
        finally:
            os.unlink(normative_file)


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def ai_system(self, temp_dirs):
        """Create complete AI system for testing."""
        storage_path, chroma_path = temp_dirs
        
        # Mock Ollama client
        mock_ollama = Mock(spec=OllamaClient)
        mock_ollama.generate_embeddings.return_value = [0.1] * 384
        mock_ollama.generate_response.return_value = "AI ответ на основе загруженных документов."
        mock_ollama.health_check.return_value = True
        
        # Create components
        with patch('ai_agent.core.document_manager.OllamaClient', return_value=mock_ollama):
            doc_manager = DocumentManager(
                storage_path=str(storage_path),
                chroma_path=str(chroma_path)
            )
        
        session_manager = SessionManager()
        query_processor = QueryProcessor(doc_manager, session_manager, mock_ollama)
        
        return {
            'doc_manager': doc_manager,
            'session_manager': session_manager,
            'query_processor': query_processor,
            'ollama_client': mock_ollama
        }
    
    def test_complete_workflow(self, ai_system):
        """Test complete AI agent workflow."""
        doc_manager = ai_system['doc_manager']
        session_manager = ai_system['session_manager']
        query_processor = ai_system['query_processor']
        
        # 1. Upload documents
        documents = []
        for i, content in enumerate([
            "Требования к поставщикам: лицензия, опыт, репутация.",
            "Процедура закупок: объявление, подача заявок, оценка.",
            "Договор должен содержать: предмет, цену, сроки."
        ]):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(content)
                doc_id = doc_manager.upload_document(f.name, metadata={'doc_type': f'test_{i}'})
                documents.append((doc_id, f.name))
        
        try:
            # Verify documents uploaded
            all_docs = doc_manager.list_documents()
            assert len(all_docs) == 3
            
            # 2. Create session and ask questions
            session_id = session_manager.create_session(user_id="test_user")
            
            # Ask about requirements
            response1 = query_processor.process_general_query(
                "Какие требования к поставщикам?", session_id
            )
            assert response1 is not None
            assert len(response1.relevant_documents) > 0
            
            # Ask about contracts
            response2 = query_processor.process_general_query(
                "Что должно быть в договоре?", session_id
            )
            assert response2 is not None
            
            # 3. Check document compliance
            test_contract = """
            Договор поставки
            Поставщик: ООО Тест
            Предмет: поставка товаров
            Цена: 50000 рублей
            Срок: 15 дней
            """
            
            compliance_response = query_processor.process_document_check(
                test_contract, session_id
            )
            assert compliance_response is not None
            assert compliance_response.query == "Проверка документа на соответствие"
            
            # 4. Verify session history
            history = session_manager.get_session_history(session_id)
            assert len(history) == 6  # 3 queries * 2 messages each
            
            # 5. Check statistics
            doc_stats = doc_manager.get_collection_stats()
            assert doc_stats['total_documents'] == 3
            assert doc_stats['total_chunks'] > 0
            
            session_stats = session_manager.get_session_stats()
            assert session_stats['total_sessions'] == 1
            assert session_stats['total_messages'] == 6
            
        finally:
            # Cleanup
            for doc_id, file_path in documents:
                doc_manager.delete_document(doc_id)
                os.unlink(file_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
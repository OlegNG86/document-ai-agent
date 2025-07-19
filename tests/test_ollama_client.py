"""Tests for OllamaClient class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_agent.core.ollama_client import OllamaClient, OllamaConnectionError


class TestOllamaClient:
    """Test cases for OllamaClient."""

    def test_init_default_values(self):
        """Test client initialization with default values."""
        with patch.dict('os.environ', {}, clear=True):
            client = OllamaClient()
            assert client.host == "http://localhost:11434"
            assert client.default_model == "llama3.1"

    def test_init_with_env_vars(self):
        """Test client initialization with environment variables."""
        with patch.dict('os.environ', {
            'OLLAMA_HOST': 'http://custom:8080',
            'OLLAMA_DEFAULT_MODEL': 'custom-model'
        }):
            client = OllamaClient()
            assert client.host == "http://custom:8080"
            assert client.default_model == "custom-model"

    def test_init_with_custom_host(self):
        """Test client initialization with custom host parameter."""
        client = OllamaClient(host="http://test:9090")
        assert client.host == "http://test:9090"

    @patch('ai_agent.core.ollama_client.Client')
    def test_health_check_success(self, mock_client_class):
        """Test successful health check."""
        mock_client = Mock()
        mock_client.list.return_value = {'models': []}
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        assert client.health_check() is True
        mock_client.list.assert_called_once()

    @patch('ai_agent.core.ollama_client.Client')
    def test_health_check_failure(self, mock_client_class):
        """Test health check failure."""
        mock_client = Mock()
        mock_client.list.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        assert client.health_check() is False

    @patch('ai_agent.core.ollama_client.Client')
    def test_list_available_models_success(self, mock_client_class):
        """Test successful model listing."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [
                {'name': 'llama3.1'},
                {'name': 'phi3'}
            ]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        models = client.list_available_models()
        
        assert models == ['llama3.1', 'phi3']
        mock_client.list.assert_called_once()

    @patch('ai_agent.core.ollama_client.Client')
    def test_list_available_models_failure(self, mock_client_class):
        """Test model listing failure."""
        mock_client = Mock()
        mock_client.list.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        
        with pytest.raises(OllamaConnectionError):
            client.list_available_models()

    @patch('ai_agent.core.ollama_client.Client')
    def test_check_model_availability_true(self, mock_client_class):
        """Test model availability check when model exists."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [{'name': 'llama3.1'}]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        assert client.check_model_availability('llama3.1') is True

    @patch('ai_agent.core.ollama_client.Client')
    def test_check_model_availability_false(self, mock_client_class):
        """Test model availability check when model doesn't exist."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [{'name': 'llama3.1'}]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        assert client.check_model_availability('nonexistent') is False

    @patch('ai_agent.core.ollama_client.Client')
    def test_check_model_availability_connection_error(self, mock_client_class):
        """Test model availability check with connection error."""
        mock_client = Mock()
        mock_client.list.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        assert client.check_model_availability('llama3.1') is False

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_response_success(self, mock_client_class):
        """Test successful response generation."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [{'name': 'llama3.1'}]
        }
        mock_client.chat.return_value = {
            'message': {'content': 'Test response'}
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        response = client.generate_response("Test prompt")
        
        assert response == "Test response"
        mock_client.chat.assert_called_once()

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_response_with_system_prompt(self, mock_client_class):
        """Test response generation with system prompt."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [{'name': 'llama3.1'}]
        }
        mock_client.chat.return_value = {
            'message': {'content': 'Test response'}
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        response = client.generate_response(
            "Test prompt", 
            system_prompt="You are a helpful assistant"
        )
        
        assert response == "Test response"
        
        # Check that system message was included
        call_args = mock_client.chat.call_args
        messages = call_args[1]['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == "You are a helpful assistant"
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == "Test prompt"

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_response_model_not_available(self, mock_client_class):
        """Test response generation with unavailable model."""
        mock_client = Mock()
        mock_client.list.return_value = {'models': []}
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        
        with pytest.raises(ValueError, match="Model 'llama3.1' is not available"):
            client.generate_response("Test prompt")

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_response_chat_error(self, mock_client_class):
        """Test response generation with chat error."""
        mock_client = Mock()
        mock_client.list.return_value = {
            'models': [{'name': 'llama3.1'}]
        }
        mock_client.chat.side_effect = Exception("Chat error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        
        with pytest.raises(OllamaConnectionError):
            client.generate_response("Test prompt")

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_embeddings_success(self, mock_client_class):
        """Test successful embeddings generation."""
        mock_client = Mock()
        mock_client.embeddings.return_value = {
            'embedding': [0.1, 0.2, 0.3]
        }
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        embeddings = client.generate_embeddings("Test text")
        
        assert embeddings == [0.1, 0.2, 0.3]
        mock_client.embeddings.assert_called_once_with(
            model="nomic-embed-text",
            prompt="Test text"
        )

    @patch('ai_agent.core.ollama_client.Client')
    def test_generate_embeddings_error(self, mock_client_class):
        """Test embeddings generation error."""
        mock_client = Mock()
        mock_client.embeddings.side_effect = Exception("Embeddings error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        
        with pytest.raises(OllamaConnectionError):
            client.generate_embeddings("Test text")

    @patch('ai_agent.core.ollama_client.Client')
    def test_pull_model_success(self, mock_client_class):
        """Test successful model pulling."""
        mock_client = Mock()
        mock_client.pull.return_value = None
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        result = client.pull_model("new-model")
        
        assert result is True
        mock_client.pull.assert_called_once_with("new-model")

    @patch('ai_agent.core.ollama_client.Client')
    def test_pull_model_error(self, mock_client_class):
        """Test model pulling error."""
        mock_client = Mock()
        mock_client.pull.side_effect = Exception("Pull error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        result = client.pull_model("new-model")
        
        assert result is False

    @patch('ai_agent.core.ollama_client.Client')
    def test_get_model_info_success(self, mock_client_class):
        """Test successful model info retrieval."""
        mock_client = Mock()
        model_info = {
            'modelfile': 'test modelfile',
            'parameters': 'test parameters'
        }
        mock_client.show.return_value = model_info
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        info = client.get_model_info("llama3.1")
        
        assert info == model_info
        mock_client.show.assert_called_once_with("llama3.1")

    @patch('ai_agent.core.ollama_client.Client')
    def test_get_model_info_error(self, mock_client_class):
        """Test model info retrieval error."""
        mock_client = Mock()
        mock_client.show.side_effect = Exception("Show error")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        info = client.get_model_info("llama3.1")
        
        assert info is None
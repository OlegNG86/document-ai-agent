"""Ollama client for AI agent communication."""

import os
import logging
from typing import List, Optional, Dict, Any
import ollama
from ollama import Client


logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Exception raised when connection to Ollama fails."""
    pass


class OllamaClient:
    """Client for interacting with local Ollama service."""
    
    def __init__(self, host: Optional[str] = None):
        """Initialize Ollama client.
        
        Args:
            host: Ollama host URL. If None, uses OLLAMA_HOST env var or default.
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = Client(host=self.host)
        self.default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5vl:latest")
        
    def health_check(self) -> bool:
        """Check if Ollama service is available.
        
        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            # Try to list models to check connectivity
            self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """Get list of available models.
        
        Returns:
            List of model names.
            
        Raises:
            OllamaConnectionError: If unable to connect to Ollama.
        """
        try:
            response = self.client.list()
            return [model['name'] for model in response['models']]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}: {e}")
    
    def check_model_availability(self, model: str) -> bool:
        """Check if a specific model is available.
        
        Args:
            model: Model name to check.
            
        Returns:
            True if model is available, False otherwise.
        """
        try:
            available_models = self.list_available_models()
            return model in available_models
        except OllamaConnectionError:
            return False
    
    def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate response using Ollama model.
        
        Args:
            prompt: User prompt/query.
            model: Model name to use. If None, uses default model.
            system_prompt: System prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens to generate.
            
        Returns:
            Generated response text.
            
        Raises:
            OllamaConnectionError: If unable to connect to Ollama.
            ValueError: If model is not available.
        """
        model = model or self.default_model
        
        if not self.check_model_availability(model):
            raise ValueError(f"Model '{model}' is not available")
        
        try:
            messages = []
            
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            messages.append({
                'role': 'user', 
                'content': prompt
            })
            
            options = {'temperature': temperature}
            if max_tokens:
                options['num_predict'] = max_tokens
            
            response = self.client.chat(
                model=model,
                messages=messages,
                options=options
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise OllamaConnectionError(f"Error generating response: {e}")
    
    def generate_embeddings(self, text: str, model: str = "nomic-embed-text") -> List[float]:
        """Generate embeddings for text.
        
        Args:
            text: Text to embed.
            model: Embedding model to use.
            
        Returns:
            List of embedding values.
            
        Raises:
            OllamaConnectionError: If unable to generate embeddings.
        """
        try:
            response = self.client.embeddings(
                model=model,
                prompt=text
            )
            return response['embedding']
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise OllamaConnectionError(f"Error generating embeddings: {e}")
    
    def pull_model(self, model: str) -> bool:
        """Pull/download a model from Ollama registry.
        
        Args:
            model: Model name to pull.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            logger.info(f"Pulling model {model}...")
            self.client.pull(model)
            logger.info(f"Model {model} pulled successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model.
        
        Args:
            model: Model name.
            
        Returns:
            Model information dict or None if not found.
        """
        try:
            response = self.client.show(model)
            return response
        except Exception as e:
            logger.error(f"Failed to get model info for {model}: {e}")
            return None
"""Ollama client for AI agent communication."""

import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import ollama
from ollama import Client

from ..utils.logging_config import get_logger
from ..utils.error_handling import (
    with_retry, with_circuit_breaker, handle_error, create_error,
    ErrorCategory, ErrorSeverity, OLLAMA_RETRY_CONFIG, EMBEDDING_RETRY_CONFIG,
    NetworkError, ExternalServiceError, is_network_error, is_temporary_error
)
from ..utils.health_monitor import health_monitor, HealthCheck, HealthStatus
from ..utils.cache_manager import cache_manager


logger = get_logger(__name__)


class OllamaConnectionError(NetworkError):
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
        
        # Register health check
        health_monitor.register_health_check("ollama_service", self._health_check)
        
    @with_retry(OLLAMA_RETRY_CONFIG, exceptions=(Exception,), logger=logger)
    def health_check(self) -> bool:
        """Check if Ollama service is available.
        
        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            start_time = time.time()
            # Try to list models to check connectivity
            self.client.list()
            
            processing_time = time.time() - start_time
            logger.debug(
                "Ollama health check successful",
                extra={
                    'operation': 'health_check',
                    'processing_time': processing_time,
                    'host': self.host
                }
            )
            return True
        except Exception as e:
            error = handle_error(
                error=e,
                error_code="OLLAMA_HEALTH_CHECK_FAILED",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.HIGH,
                details={'host': self.host},
                suggestions=[
                    "Check if Ollama service is running (ollama serve)",
                    "Verify OLLAMA_HOST environment variable",
                    "Check network connectivity to Ollama service"
                ],
                context={'operation': 'health_check', 'host': self.host}
            )
            return False
    
    @with_retry(OLLAMA_RETRY_CONFIG, exceptions=(Exception,), logger=logger)
    def list_available_models(self) -> List[str]:
        """Get list of available models.
        
        Returns:
            List of model names.
            
        Raises:
            OllamaConnectionError: If unable to connect to Ollama.
        """
        try:
            start_time = time.time()
            logger.debug("Listing available Ollama models", extra={'operation': 'list_models'})
            
            response = self.client.list()
            models = [model['name'] for model in response['models']]
            
            processing_time = time.time() - start_time
            logger.info(
                f"Retrieved {len(models)} available models",
                extra={
                    'operation': 'list_models',
                    'processing_time': processing_time,
                    'model_count': len(models),
                    'models': models[:5]  # Log first 5 models
                }
            )
            
            return models
        except Exception as e:
            error = handle_error(
                error=e,
                error_code="OLLAMA_LIST_MODELS_FAILED",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM,
                details={'host': self.host},
                suggestions=[
                    "Check Ollama service status",
                    "Verify network connectivity",
                    "Try restarting Ollama service"
                ],
                context={'operation': 'list_models'}
            )
            raise OllamaConnectionError(error.error_info, e)
    
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
    
    @with_circuit_breaker(
        failure_threshold=3,
        recovery_timeout=30.0,
        expected_exception=Exception
    )
    @with_retry(OLLAMA_RETRY_CONFIG, exceptions=(Exception,), logger=logger)
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
        start_time = time.time()
        
        logger.debug(
            f"Generating response with model {model}",
            extra={
                'operation': 'generate_response',
                'model': model,
                'prompt_length': len(prompt),
                'temperature': temperature,
                'max_tokens': max_tokens
            }
        )
        
        if not self.check_model_availability(model):
            error = create_error(
                error_code="OLLAMA_MODEL_NOT_AVAILABLE",
                message=f"Model '{model}' is not available",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                details={'requested_model': model, 'available_models': self.list_available_models()},
                suggestions=[
                    f"Pull the model using: ollama pull {model}",
                    "Check available models with: ollama list",
                    "Use a different model that is available"
                ]
            )
            raise ValueError(error.error_info.message)
        
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
            
            response_text = response['message']['content']
            processing_time = time.time() - start_time
            
            logger.info(
                f"Generated response successfully",
                extra={
                    'operation': 'generate_response',
                    'model': model,
                    'processing_time': processing_time,
                    'prompt_length': len(prompt),
                    'response_length': len(response_text),
                    'temperature': temperature
                }
            )
            
            return response_text
            
        except Exception as e:
            processing_time = time.time() - start_time
            error = handle_error(
                error=e,
                error_code="OLLAMA_RESPONSE_GENERATION_FAILED",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.HIGH,
                details={
                    'model': model,
                    'prompt_length': len(prompt),
                    'processing_time': processing_time,
                    'temperature': temperature
                },
                suggestions=[
                    "Check Ollama service status",
                    "Verify model is properly loaded",
                    "Try with a different model",
                    "Reduce prompt length if too long"
                ],
                context={'operation': 'generate_response', 'model': model}
            )
            raise OllamaConnectionError(error.error_info, e)
    
    @with_retry(EMBEDDING_RETRY_CONFIG, exceptions=(Exception,), logger=logger, should_retry=is_temporary_error)
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
        start_time = time.time()
        
        logger.debug(
            f"Generating embeddings with model {model}",
            extra={
                'operation': 'generate_embeddings',
                'model': model,
                'text_length': len(text)
            }
        )
        
        # Check cache first
        cached_embedding = cache_manager.query_cache.get_embedding(text, model)
        if cached_embedding is not None:
            logger.debug("Returning cached embedding")
            return cached_embedding
        
        try:
            response = self.client.embeddings(
                model=model,
                prompt=text
            )
            
            embeddings = response['embedding']
            processing_time = time.time() - start_time
            
            # Cache the embedding
            cache_manager.query_cache.cache_embedding(text, embeddings, model, ttl=7200)  # 2 hours
            
            logger.debug(
                f"Generated embeddings successfully",
                extra={
                    'operation': 'generate_embeddings',
                    'model': model,
                    'processing_time': processing_time,
                    'text_length': len(text),
                    'embedding_dimension': len(embeddings)
                }
            )
            
            return embeddings
            
        except Exception as e:
            processing_time = time.time() - start_time
            error = handle_error(
                error=e,
                error_code="OLLAMA_EMBEDDINGS_GENERATION_FAILED",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.HIGH,
                details={
                    'model': model,
                    'text_length': len(text),
                    'processing_time': processing_time
                },
                suggestions=[
                    f"Check if embedding model '{model}' is available",
                    f"Pull the model using: ollama pull {model}",
                    "Try with a different embedding model",
                    "Check Ollama service status"
                ],
                context={'operation': 'generate_embeddings', 'model': model}
            )
            raise OllamaConnectionError(error.error_info, e)
    
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
    
    def _health_check(self) -> HealthCheck:
        """Health check for Ollama service.
        
        Returns:
            HealthCheck result.
        """
        try:
            start_time = time.time()
            
            # Try to list models to check connectivity
            models = self.client.list()
            response_time = time.time() - start_time
            
            model_count = len(models.get('models', []))
            
            if model_count == 0:
                status = HealthStatus.WARNING
                message = "Ollama service connected but no models available"
            else:
                status = HealthStatus.HEALTHY
                message = f"Ollama service healthy with {model_count} models"
            
            return HealthCheck(
                name="ollama_service",
                status=status,
                message=message,
                details={
                    'host': self.host,
                    'model_count': model_count,
                    'default_model': self.default_model,
                    'available_models': [m['name'] for m in models.get('models', [])][:5]  # First 5 models
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheck(
                name="ollama_service",
                status=HealthStatus.CRITICAL,
                message=f"Ollama service unavailable: {e}",
                details={
                    'host': self.host,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'is_network_error': is_network_error(e)
                },
                timestamp=datetime.now()
            )
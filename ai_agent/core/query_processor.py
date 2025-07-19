"""Query processor for handling user queries and generating responses."""

import uuid
import logging
import time
from typing import List, Dict, Any, Optional

from ..models.query_response import QueryResponse
from ..models.message import MessageType
from .ollama_client import OllamaClient, OllamaConnectionError
from .document_manager import DocumentManager, DocumentManagerError
from ..models.document import DocumentCategory
from .session_manager import SessionManager, SessionManagerError


logger = logging.getLogger(__name__)


class QueryProcessorError(Exception):
    """Exception raised for query processing errors."""
    pass


class QueryProcessor:
    """Processes user queries and generates responses using documents and LLM."""
    
    def __init__(
        self,
        document_manager: DocumentManager,
        session_manager: SessionManager,
        ollama_client: Optional[OllamaClient] = None
    ):
        """Initialize query processor.
        
        Args:
            document_manager: Document manager instance.
            session_manager: Session manager instance.
            ollama_client: Ollama client instance. If None, creates new one.
        """
        self.document_manager = document_manager
        self.session_manager = session_manager
        self.ollama_client = ollama_client or OllamaClient()
        
        # Default prompts
        self.system_prompt = """Вы - AI помощник для работы с нормативной документацией по закупкам.
Используйте предоставленные документы для ответа на вопросы пользователей.
Всегда указывайте источники информации и ссылайтесь на конкретные документы.
Если информации недостаточно в предоставленных документах, честно об этом сообщите.
Отвечайте на русском языке, будьте точными и профессиональными."""
        
        self.document_check_prompt = """Проанализируйте предоставленный документ на соответствие нормативным требованиям по закупкам.
Используйте базу знаний нормативных документов для проверки.
Укажите:
1. Найденные нарушения или несоответствия
2. Ссылки на соответствующие нормативы
3. Рекомендации по устранению проблем
4. Общее заключение о возможности заключения договора

Если документ соответствует всем требованиям, подтвердите это."""
    
    def process_general_query(self, query: str, session_id: str) -> QueryResponse:
        """Process a general user query.
        
        Args:
            query: User query.
            session_id: Session identifier.
            
        Returns:
            Query response with answer and metadata.
            
        Raises:
            QueryProcessorError: If processing fails.
        """
        start_time = time.time()
        
        try:
            # Add user message to session
            user_message_id = self.session_manager.add_user_message(session_id, query)
            
            # Get relevant context from documents
            relevant_chunks = self._get_relevant_context(query)
            
            # Build context for LLM
            context = self._build_context_string(relevant_chunks)
            
            # Get conversation history for context
            history = self._get_conversation_context(session_id)
            
            # Generate response
            full_prompt = self._build_query_prompt(query, context, history)
            response_text = self.ollama_client.generate_response(
                prompt=full_prompt,
                system_prompt=self.system_prompt
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create response object
            response_id = str(uuid.uuid4())
            response = QueryResponse(
                id=response_id,
                query=query,
                response=response_text,
                session_id=session_id,
                processing_time=processing_time
            )
            
            # Add relevant document IDs
            for chunk in relevant_chunks:
                doc_id = chunk['metadata'].get('document_id')
                if doc_id:
                    response.add_relevant_document(doc_id)
            
            # Set confidence score based on relevance
            if relevant_chunks:
                avg_relevance = sum(chunk.get('relevance_score', 0) for chunk in relevant_chunks) / len(relevant_chunks)
                response.set_confidence_score(min(avg_relevance, 1.0))
            else:
                response.set_confidence_score(0.3)  # Low confidence without relevant docs
            
            # Add assistant message to session
            assistant_metadata = {
                'response_id': response_id,
                'relevant_documents': response.relevant_documents,
                'confidence_score': response.confidence_score,
                'processing_time': processing_time
            }
            self.session_manager.add_assistant_message(
                session_id=session_id,
                content=response_text,
                metadata=assistant_metadata,
                parent_message_id=user_message_id
            )
            
            logger.info(f"Processed general query in {processing_time:.2f}s")
            return response
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error: {e}")
            raise QueryProcessorError(f"AI service unavailable: {e}")
        except DocumentManagerError as e:
            logger.error(f"Document search error: {e}")
            raise QueryProcessorError(f"Document search failed: {e}")
        except SessionManagerError as e:
            logger.error(f"Session error: {e}")
            raise QueryProcessorError(f"Session management failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing query: {e}")
            raise QueryProcessorError(f"Query processing failed: {e}")
    
    def process_document_check(
        self, 
        document_content: str, 
        session_id: str,
        reference_document_ids: Optional[List[str]] = None
    ) -> QueryResponse:
        """Process document compliance check.
        
        Args:
            document_content: Content of document to check.
            session_id: Session identifier.
            reference_document_ids: Optional list of specific reference document IDs to use.
            
        Returns:
            Query response with compliance analysis.
            
        Raises:
            QueryProcessorError: If processing fails.
        """
        start_time = time.time()
        
        try:
            # Add user message to session
            user_message_id = self.session_manager.add_user_message(
                session_id=session_id,
                content="Проверка документа на соответствие нормативным требованиям",
                metadata={'document_content_length': len(document_content)}
            )
            
            # Search for relevant normative documents
            search_query = "нормативные требования закупки договор соответствие"
            
            if reference_document_ids:
                # Use specific reference documents
                relevant_chunks = self._get_context_from_specific_documents(
                    query=search_query,
                    document_ids=reference_document_ids,
                    top_k=10
                )
            else:
                # Search only in reference documents
                relevant_chunks = self._get_relevant_context(
                    query=search_query,
                    top_k=10,
                    category_filter=DocumentCategory.REFERENCE
                )
            
            # Build context for compliance check
            normative_context = self._build_context_string(relevant_chunks)
            
            # Generate compliance analysis
            full_prompt = self._build_document_check_prompt(document_content, normative_context)
            response_text = self.ollama_client.generate_response(
                prompt=full_prompt,
                system_prompt=self.document_check_prompt,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create response object
            response_id = str(uuid.uuid4())
            response = QueryResponse(
                id=response_id,
                query="Проверка документа на соответствие",
                response=response_text,
                session_id=session_id,
                processing_time=processing_time
            )
            
            # Add relevant normative document IDs
            for chunk in relevant_chunks:
                doc_id = chunk['metadata'].get('document_id')
                if doc_id:
                    response.add_relevant_document(doc_id)
            
            # Set confidence based on available normative documents
            if relevant_chunks:
                response.set_confidence_score(0.8)  # High confidence with normative docs
            else:
                response.set_confidence_score(0.4)  # Lower without reference docs
            
            # Add assistant message to session
            assistant_metadata = {
                'response_id': response_id,
                'check_type': 'document_compliance',
                'relevant_documents': response.relevant_documents,
                'confidence_score': response.confidence_score,
                'processing_time': processing_time
            }
            self.session_manager.add_assistant_message(
                session_id=session_id,
                content=response_text,
                metadata=assistant_metadata,
                parent_message_id=user_message_id
            )
            
            logger.info(f"Processed document check in {processing_time:.2f}s")
            return response
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error during document check: {e}")
            raise QueryProcessorError(f"AI service unavailable: {e}")
        except DocumentManagerError as e:
            logger.error(f"Document search error during compliance check: {e}")
            raise QueryProcessorError(f"Normative document search failed: {e}")
        except SessionManagerError as e:
            logger.error(f"Session error during document check: {e}")
            raise QueryProcessorError(f"Session management failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during document check: {e}")
            raise QueryProcessorError(f"Document check failed: {e}")
    
    def _get_relevant_context(
        self, 
        query: str, 
        top_k: int = 5,
        category_filter: Optional[DocumentCategory] = None,
        tags_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get relevant document chunks for a query.
        
        Args:
            query: Search query.
            top_k: Number of top results to return.
            category_filter: Filter by document category.
            tags_filter: Filter by document tags.
            
        Returns:
            List of relevant document chunks.
        """
        try:
            return self.document_manager.search_similar_chunks(
                query=query,
                top_k=top_k,
                category_filter=category_filter,
                tags_filter=tags_filter
            )
        except DocumentManagerError as e:
            logger.warning(f"Failed to get relevant context: {e}")
            return []
    
    def _get_context_from_specific_documents(
        self, 
        query: str, 
        document_ids: List[str], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Get relevant chunks from specific documents.
        
        Args:
            query: Search query.
            document_ids: List of document IDs to search in.
            top_k: Number of top results to return.
            
        Returns:
            List of relevant document chunks from specified documents.
        """
        try:
            # Get all chunks and filter by document IDs
            all_chunks = self.document_manager.search_similar_chunks(query, top_k * 3)
            
            # Filter by document IDs
            filtered_chunks = []
            for chunk in all_chunks:
                if chunk['metadata'].get('document_id') in document_ids:
                    filtered_chunks.append(chunk)
                    if len(filtered_chunks) >= top_k:
                        break
            
            return filtered_chunks
            
        except DocumentManagerError as e:
            logger.warning(f"Failed to get context from specific documents: {e}")
            return []
    
    def _build_context_string(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from document chunks.
        
        Args:
            chunks: List of document chunks.
            
        Returns:
            Formatted context string.
        """
        if not chunks:
            return "Релевантные документы не найдены."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            doc_title = metadata.get('title', 'Неизвестный документ')
            content = chunk.get('content', '')
            
            context_parts.append(f"Документ {i}: {doc_title}\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _get_conversation_context(self, session_id: str, max_messages: int = 6) -> str:
        """Get conversation context from session history.
        
        Args:
            session_id: Session identifier.
            max_messages: Maximum number of recent messages to include.
            
        Returns:
            Formatted conversation context.
        """
        try:
            messages = self.session_manager.get_session_history(session_id, max_messages)
            
            if not messages:
                return ""
            
            context_parts = ["Предыдущий контекст разговора:"]
            for message in messages[-max_messages:]:
                role = "Пользователь" if message.is_user_message() else "Ассистент"
                content = message.content[:200] + "..." if len(message.content) > 200 else message.content
                context_parts.append(f"{role}: {content}")
            
            return "\n".join(context_parts)
            
        except SessionManagerError:
            return ""
    
    def _build_query_prompt(self, query: str, context: str, history: str) -> str:
        """Build prompt for general query processing.
        
        Args:
            query: User query.
            context: Relevant document context.
            history: Conversation history.
            
        Returns:
            Formatted prompt.
        """
        prompt_parts = []
        
        if context:
            prompt_parts.append(f"Релевантная информация из документов:\n{context}")
        
        if history:
            prompt_parts.append(f"\n{history}")
        
        prompt_parts.append(f"\nВопрос пользователя: {query}")
        prompt_parts.append("\nОтветьте на вопрос, используя информацию из предоставленных документов. Укажите источники.")
        
        return "\n".join(prompt_parts)
    
    def _build_document_check_prompt(self, document_content: str, normative_context: str) -> str:
        """Build prompt for document compliance check.
        
        Args:
            document_content: Content of document to check.
            normative_context: Relevant normative documents.
            
        Returns:
            Formatted prompt.
        """
        prompt_parts = []
        
        if normative_context:
            prompt_parts.append(f"Нормативные требования:\n{normative_context}")
        
        prompt_parts.append(f"\nПроверяемый документ:\n{document_content}")
        prompt_parts.append("\nПроведите анализ соответствия документа нормативным требованиям.")
        
        return "\n".join(prompt_parts)
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get query processing statistics.
        
        Returns:
            Dictionary with statistics.
        """
        # This is a placeholder for future implementation
        # Could track metrics like average processing time, query types, etc.
        return {
            'total_queries_processed': 0,
            'average_processing_time': 0.0,
            'document_checks_performed': 0
        }
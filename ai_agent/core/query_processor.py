"""Query processor for handling user queries and generating responses."""

import uuid
import logging
import time
import os
from typing import List, Dict, Any, Optional

from ..models.query_response import QueryResponse
from ..models.message import MessageType
from .ollama_client import OllamaClient, OllamaConnectionError
from .document_manager import DocumentManager, DocumentManagerError
from ..models.document import DocumentCategory
from .session_manager import SessionManager, SessionManagerError
from ..utils.decision_tree import (
    DecisionTreeBuilder, DecisionTreeVisualizer, QueryType, DetailLevel,
    get_decision_tree_settings
)
from ..utils.tree_exporter import DecisionTreeExporter


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
        ollama_client: Optional[OllamaClient] = None,
        show_decision_tree: Optional[bool] = None,
        web_visualization: Optional[bool] = None
    ):
        """Initialize query processor.
        
        Args:
            document_manager: Document manager instance.
            session_manager: Session manager instance.
            ollama_client: Ollama client instance. If None, creates new one.
            show_decision_tree: Whether to show decision trees. If None, uses environment setting.
            web_visualization: Whether to enable web visualization. If None, uses environment setting.
        """
        self.document_manager = document_manager
        self.session_manager = session_manager
        self.ollama_client = ollama_client or OllamaClient()
        
        # Decision tree components
        self.tree_builder = DecisionTreeBuilder()
        self.tree_visualizer = DecisionTreeVisualizer()
        self.tree_exporter = DecisionTreeExporter()
        
        # Decision tree settings
        self.decision_tree_settings = get_decision_tree_settings()
        if show_decision_tree is not None:
            self.decision_tree_settings['enabled'] = show_decision_tree
            
        # Web visualization settings
        self.web_visualization = web_visualization if web_visualization is not None else \
            os.environ.get('VISUALIZATION_ENABLED', 'false').lower() in ['true', '1', 'yes']
        
        # Confidence breakdown storage
        self._last_confidence_breakdown = None
        
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
            
            # Generate decision tree if enabled
            decision_tree_output = ""
            if self.decision_tree_settings['enabled']:
                decision_tree_output = self._generate_decision_tree_for_query(
                    query=query,
                    has_context=bool(relevant_chunks),
                    query_type=QueryType.GENERAL_QUESTION,
                    relevant_chunks=relevant_chunks,
                    response_text=response_text,
                    response_metadata={}
                )
            
            # Create response object
            response_id = str(uuid.uuid4())
            response = QueryResponse(
                id=response_id,
                query=query,
                response=response_text,
                session_id=session_id,
                processing_time=processing_time
            )
            
            # Add decision tree to response if available
            if decision_tree_output:
                response.response = f"{response_text}\n\n{decision_tree_output}"
            
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
        reference_document_ids: Optional[List[str]] = None,
        document_filename: Optional[str] = None
    ) -> QueryResponse:
        """Process document compliance check.
        
        Args:
            document_content: Content of document to check.
            session_id: Session identifier.
            reference_document_ids: Optional list of specific reference document IDs to use.
            document_filename: Optional filename of the document being checked.
            
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
            
            # Generate decision tree if enabled
            decision_tree_output = ""
            if self.decision_tree_settings['enabled']:
                decision_tree_output = self._generate_decision_tree_for_query(
                    query="Проверка документа на соответствие",
                    has_context=bool(relevant_chunks),
                    query_type=QueryType.COMPLIANCE_CHECK,
                    relevant_chunks=relevant_chunks,
                    response_text=response_text,
                    response_metadata={},
                    document_filename=document_filename
                )
            
            # Create response object
            response_id = str(uuid.uuid4())
            response = QueryResponse(
                id=response_id,
                query="Проверка документа на соответствие",
                response=response_text,
                session_id=session_id,
                processing_time=processing_time
            )
            
            # Add decision tree to response if available
            if decision_tree_output:
                response.response = f"{response_text}\n\n{decision_tree_output}"
            
            # Add relevant normative document IDs
            for chunk in relevant_chunks:
                doc_id = chunk['metadata'].get('document_id')
                if doc_id:
                    response.add_relevant_document(doc_id)
            
            # Get confidence from decision tree if available
            if decision_tree_output and hasattr(self, '_last_generated_tree'):
                # Calculate confidence components for tree
                context_confidence = self._calculate_context_confidence(relevant_chunks or [])
                analysis_confidence = self._calculate_analysis_confidence({})
                
                # Get confidence from tree
                confidence_score, confidence_breakdown = self._calculate_compliance_confidence_from_tree(
                    self._last_generated_tree,
                    context_confidence,
                    analysis_confidence
                )
                response.set_confidence_score(confidence_score)
                response.confidence_breakdown = confidence_breakdown
            else:
                # Fallback to simple calculation
                if relevant_chunks:
                    response.set_confidence_score(0.8)
                else:
                    response.set_confidence_score(0.4)
            
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
    
    def _generate_decision_tree_for_query(
        self,
        query: str,
        has_context: bool,
        query_type: QueryType,
        relevant_chunks: List[Dict] = None,
        response_text: str = "",
        response_metadata: Dict = None,
        document_filename: str = None
    ) -> str:
        """Generate decision tree visualization for a query.
        
        Args:
            query: The user query.
            has_context: Whether relevant context was found.
            query_type: Type of the query.
            relevant_chunks: List of relevant document chunks for confidence calculation.
            response_text: AI response text for confidence calculation.
            response_metadata: Response metadata for confidence calculation.
            document_filename: Optional filename of the document being processed.
            
        Returns:
            Decision tree visualization string.
        """
        try:
            # Build appropriate decision tree based on query type
            if query_type == QueryType.COMPLIANCE_CHECK:
                # Calculate dynamic confidence scores
                context_confidence = self._calculate_context_confidence(relevant_chunks or [])
                analysis_confidence = self._calculate_analysis_confidence(response_metadata)
                compliance_confidence = self._calculate_compliance_confidence(response_text)
                
                tree = self.tree_builder.build_compliance_check_tree(
                    has_reference_docs=has_context,
                    query_context=query,
                    context_confidence=context_confidence,
                    analysis_confidence=analysis_confidence,
                    compliance_confidence=compliance_confidence
                )
            else:
                tree = self.tree_builder.build_general_query_tree(query, has_context)
            
            # Export tree for web visualization if enabled
            visualization_url = ""
            logger.info(f"Web visualization enabled: {self.web_visualization}")
            if self.web_visualization:
                try:
                    logger.info(f"Attempting to export decision tree for query type: {query_type.value}")
                    tree_path = self.tree_exporter.export_tree(tree, query_type.value, query, document_filename)
                    if tree_path:
                        logger.info(f"Decision tree exported successfully to: {tree_path}")
                        visualization_url = self.tree_exporter.get_visualization_url(tree_path)
                    else:
                        logger.warning("Decision tree export returned None")
                except Exception as e:
                    logger.error(f"Failed to export decision tree: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Visualize the tree
            tree_output = self.tree_visualizer.visualize_tree(
                tree=tree,
                detail_level=self.decision_tree_settings['detail_level'],
                max_width=self.decision_tree_settings['max_width']
            )
            
            # Add header
            header = "\n" + "="*50 + "\n🌳 АНАЛИЗ ПРОЦЕССА ПРИНЯТИЯ РЕШЕНИЙ\n" + "="*50
            
            # Add visualization URL if available
            if visualization_url:
                web_viz_info = f"\n\n🔗 Интерактивная визуализация доступна по адресу: {visualization_url}"
                return f"{header}\n{tree_output}{web_viz_info}"
            else:
                return f"{header}\n{tree_output}"
            
        except Exception as e:
            logger.warning(f"Failed to generate decision tree: {e}")
            return ""
    
    def set_decision_tree_enabled(self, enabled: bool) -> None:
        """Enable or disable decision tree visualization.
        
        Args:
            enabled: Whether to enable decision trees.
        """
        self.decision_tree_settings['enabled'] = enabled
    
    def set_decision_tree_detail_level(self, detail_level: DetailLevel) -> None:
        """Set decision tree detail level.
        
        Args:
            detail_level: Detail level to use.
        """
        self.decision_tree_settings['detail_level'] = detail_level
    
    def set_web_visualization(self, enabled: bool) -> None:
        """Enable or disable web visualization.
        
        Args:
            enabled: Whether to enable web visualization.
        """
        self.web_visualization = enabled
    
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
            'document_checks_performed': 0,
            'decision_tree_enabled': self.decision_tree_settings['enabled'],
            'web_visualization_enabled': self.web_visualization
        }
    
    def _calculate_context_confidence(self, relevant_chunks: List[Dict]) -> float:
        """Calculate confidence in found context based on relevance and quantity.
        
        Args:
            relevant_chunks: List of relevant document chunks.
            
        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not relevant_chunks:
            return 0.0
        
        # Base confidence on number of chunks (more chunks = higher confidence)
        chunk_count_factor = min(len(relevant_chunks) / 10.0, 1.0)  # Max at 10 chunks
        
        # Calculate average relevance score if available
        relevance_scores = []
        for chunk in relevant_chunks:
            # Try to get relevance score from metadata
            score = chunk.get('metadata', {}).get('relevance_score', 0.7)  # Default 0.7
            relevance_scores.append(score)
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.7
        
        # Combine factors
        confidence = (chunk_count_factor * 0.4 + avg_relevance * 0.6)
        return min(max(confidence, 0.0), 1.0)  # Clamp between 0 and 1
    
    def _calculate_analysis_confidence(self, response_metadata: Dict = None) -> float:
        """Calculate confidence in analysis capability based on response metadata.
        
        Args:
            response_metadata: Metadata from AI response.
            
        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not response_metadata:
            return 0.7  # Default medium confidence
        
        # Factors that could indicate analysis confidence:
        # - Response length (longer = more detailed analysis)
        # - Presence of specific keywords
        # - Model confidence if available
        
        confidence = 0.7  # Base confidence
        
        # Adjust based on available metadata
        if 'model_confidence' in response_metadata:
            confidence = response_metadata['model_confidence']
        
        return min(max(confidence, 0.0), 1.0)
    
    def _calculate_compliance_confidence(self, response_text: str) -> float:
        """Calculate confidence in compliance analysis based on response content.
        
        Args:
            response_text: AI response text to analyze.
            
        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if not response_text:
            return 0.0
        
        # Keywords that indicate thorough compliance analysis
        compliance_keywords = [
            'нарушения', 'несоответствия', 'требования', 'нормативы',
            'статья', 'закон', 'рекомендации', 'заключение',
            'соответствует', 'не соответствует', 'устранить'
        ]
        
        # Count keyword occurrences
        text_lower = response_text.lower()
        keyword_count = sum(1 for keyword in compliance_keywords if keyword in text_lower)
        
        # Base confidence on response length and keyword density
        response_length = len(response_text)
        length_factor = min(response_length / 1000.0, 1.0)  # Normalize to 1000 chars
        keyword_factor = min(keyword_count / len(compliance_keywords), 1.0)
        
        # Check for structured analysis (numbered lists, sections)
        structure_indicators = ['1.', '2.', '3.', '•', '-', 'Рекомендации', 'Заключение']
        structure_count = sum(1 for indicator in structure_indicators if indicator in response_text)
        structure_factor = min(structure_count / 5.0, 1.0)
        
        # Combine factors
        confidence = (length_factor * 0.3 + keyword_factor * 0.4 + structure_factor * 0.3)
        
        # Ensure minimum confidence for any response
        confidence = max(confidence, 0.4)
        
        return min(confidence, 1.0)
    
    def _calculate_compliance_confidence_from_tree(
        self, 
        tree: Dict, 
        context_confidence: float, 
        analysis_confidence: float
    ) -> tuple[float, Dict[str, float]]:
        """Calculate compliance confidence from decision tree and component confidences.
        
        Args:
            tree: Decision tree structure.
            context_confidence: Confidence in found context.
            analysis_confidence: Confidence in analysis capability.
            
        Returns:
            Tuple of (overall_confidence, confidence_breakdown).
        """
        # Extract compliance confidence from tree if available
        compliance_confidence = 0.7  # Default
        
        if tree and 'metadata' in tree:
            compliance_confidence = tree['metadata'].get('compliance_confidence', 0.7)
        
        # Calculate weighted overall confidence
        weights = {
            'context': 0.3,
            'analysis': 0.4,
            'compliance': 0.3
        }
        
        overall_confidence = (
            context_confidence * weights['context'] +
            analysis_confidence * weights['analysis'] +
            compliance_confidence * weights['compliance']
        )
        
        confidence_breakdown = {
            'context_confidence': context_confidence,
            'analysis_confidence': analysis_confidence,
            'compliance_confidence': compliance_confidence,
            'overall_confidence': overall_confidence
        }
        
        return overall_confidence, confidence_breakdown
    

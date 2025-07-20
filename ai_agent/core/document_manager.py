"""Document manager for handling document upload, processing and search."""

import os
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

import chromadb
from chromadb.config import Settings

from ..models.document import Document, DocumentCategory
from .ollama_client import OllamaClient, OllamaConnectionError
from ..utils.logging_config import get_logger
from ..utils.error_handling import (
    with_retry, handle_error, create_error,
    ErrorCategory, ErrorSeverity, DATABASE_RETRY_CONFIG, FILE_IO_RETRY_CONFIG,
    ProcessingError, ValidationError, ResourceError, is_temporary_error
)
from ..utils.health_monitor import health_monitor, HealthCheck, HealthStatus
from ..utils.cache_manager import cache_manager
from ..utils.chunk_optimizer import optimized_chunker
from ..utils.async_processor import async_processor
from ..utils.performance_monitor import performance_tracker
from ..utils.file_processor import file_processor, FileProcessorError


logger = get_logger(__name__)


class DocumentManagerError(ProcessingError):
    """Exception raised for document management errors."""
    pass


class DocumentManager:
    """Manages document storage, indexing and search using ChromaDB."""
    
    def __init__(
        self, 
        storage_path: str = "data/documents",
        chroma_path: str = "data/chroma_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """Initialize document manager.
        
        Args:
            storage_path: Path to store uploaded documents.
            chroma_path: Path for ChromaDB storage.
            chunk_size: Size of text chunks for vectorization.
            chunk_overlap: Overlap between chunks.
        """
        self.storage_path = Path(storage_path)
        self.chroma_path = Path(chroma_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create directories if they don't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents",
            metadata={"description": "Document knowledge base"}
        )
        
        # Initialize Ollama client for embeddings
        self.ollama_client = OllamaClient()
        
        # Register health check
        health_monitor.register_health_check("document_storage", self._health_check)
        
    def upload_document(
        self, 
        file_path: str, 
        metadata: Optional[Dict[str, Any]] = None,
        category: DocumentCategory = DocumentCategory.GENERAL,
        tags: Optional[List[str]] = None
    ) -> str:
        """Upload and process a document.
        
        Args:
            file_path: Path to the document file.
            metadata: Additional metadata for the document.
            category: Document category (reference, target, general).
            tags: List of tags for the document.
            
        Returns:
            Document ID.
            
        Raises:
            DocumentManagerError: If upload fails.
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        logger.info(
            f"Starting document upload: {file_path.name}",
            extra={
                'operation': 'upload_document',
                'file_path': str(file_path),
                'category': category.value,
                'tags': tags or []
            }
        )
        
        # Validate file existence
        if not file_path.exists():
            error = create_error(
                error_code="DOCUMENT_FILE_NOT_FOUND",
                message=f"File not found: {file_path}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                details={'file_path': str(file_path)},
                suggestions=[
                    "Check if the file path is correct",
                    "Verify file permissions",
                    "Ensure the file exists"
                ]
            )
            raise DocumentManagerError(error.error_info, error)
        
        # Validate file type using file processor
        if not file_processor.is_supported_format(file_path):
            supported_types = file_processor.get_supported_extensions()
            error = create_error(
                error_code="DOCUMENT_UNSUPPORTED_FILE_TYPE",
                message=f"Unsupported file type: {file_path.suffix}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                details={
                    'file_type': file_path.suffix,
                    'supported_types': supported_types
                },
                suggestions=[
                    f"Convert file to one of supported formats: {', '.join(supported_types)}",
                    "Check if required libraries are installed for this format"
                ]
            )
            raise DocumentManagerError(error.error_info, error)
        
        try:
            # Extract file content using file processor
            content, file_metadata = file_processor.extract_text(file_path)
            
            # Validate extracted content
            if not file_processor.validate_extracted_text(content):
                error = create_error(
                    error_code="DOCUMENT_EMPTY_OR_INVALID_CONTENT",
                    message="Document content is empty or invalid",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    details={
                        'file_path': str(file_path),
                        'content_length': len(content) if content else 0,
                        'file_metadata': file_metadata
                    },
                    suggestions=[
                        "Check if the file contains readable text content",
                        "Verify file is not corrupted",
                        "Try opening the file manually to check content",
                        "Check file encoding if it's a text file"
                    ]
                )
                raise DocumentManagerError(error.error_info, error)
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Merge file metadata with user metadata
            combined_metadata = {**(metadata or {}), **file_metadata}
            
            # Create document object
            document = Document(
                id=doc_id,
                title=file_path.stem,
                content=content,
                file_path=file_path,
                file_type=file_path.suffix[1:],  # Remove the dot
                category=category,
                tags=tags or [],
                metadata=combined_metadata
            )
            
            # Store file and process chunks
            self._store_document_file(document, content)
            
            # Use optimized chunking or async processing for large documents
            if async_processor.should_process_async(content):
                # For very large documents, use async processing
                task_id = f"upload_{doc_id}"
                task = async_processor.submit_task(
                    task_id=task_id,
                    file_path=file_path,
                    content=content,
                    metadata={'document_id': doc_id, 'category': category.value}
                )
                
                # Wait for completion (with timeout)
                result = async_processor.wait_for_task(task_id, timeout=300)  # 5 minutes
                if result:
                    chunks = [chunk['content'] for chunk in result['chunks']]
                    logger.info(f"Async processing completed: {result['successful_chunks']}/{result['total_chunks']} chunks")
                else:
                    # Fallback to synchronous processing
                    logger.warning("Async processing failed, falling back to sync")
                    chunks, _ = optimized_chunker.chunk_document(content, file_path.name)
            else:
                # Use optimized chunking for regular documents
                chunks, chunk_metadata = optimized_chunker.chunk_document(content, file_path.name)
                logger.debug(f"Optimized chunking: {chunk_metadata}")
            
            self._store_document_chunks(document, chunks)
            
            processing_time = time.time() - start_time
            logger.info(
                f"Document uploaded successfully: {doc_id}",
                extra={
                    'operation': 'upload_document',
                    'document_id': doc_id,
                    'processing_time': processing_time,
                    'content_length': len(content),
                    'chunk_count': len(chunks),
                    'category': category.value
                }
            )
            
            return doc_id
            
        except DocumentManagerError:
            # Re-raise DocumentManagerError as-is
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            error = handle_error(
                error=e,
                error_code="DOCUMENT_UPLOAD_FAILED",
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.HIGH,
                details={
                    'file_path': str(file_path),
                    'processing_time': processing_time,
                    'category': category.value
                },
                suggestions=[
                    "Check file permissions and accessibility",
                    "Verify ChromaDB connection",
                    "Check available disk space",
                    "Try uploading a smaller file first"
                ],
                context={'operation': 'upload_document', 'file_path': str(file_path)}
            )
            raise DocumentManagerError(error.error_info, e)
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks.
        
        Args:
            document_id: ID of document to delete.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        try:
            # Delete from ChromaDB
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(1000)]  # Max chunks assumption
            
            # Get existing chunk IDs for this document
            existing_chunks = self.collection.get(
                where={"document_id": document_id}
            )
            
            if existing_chunks['ids']:
                self.collection.delete(ids=existing_chunks['ids'])
            
            # Delete stored file
            for file_path in self.storage_path.glob(f"{document_id}_*"):
                file_path.unlink()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a document.
        
        Args:
            document_id: ID of the document.
            
        Returns:
            Document information dict or None if not found.
        """
        try:
            # Get chunks for this document
            chunks_data = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not chunks_data['ids']:
                return None
            
            # Get metadata from first chunk
            first_chunk_metadata = chunks_data['metadatas'][0]
            
            return {
                'id': document_id,
                'title': first_chunk_metadata.get('title', 'Unknown'),
                'file_type': first_chunk_metadata.get('file_type', 'unknown'),
                'category': first_chunk_metadata.get('category', 'general'),
                'tags': first_chunk_metadata.get('tags', '').split(',') if first_chunk_metadata.get('tags') else [],
                'upload_date': first_chunk_metadata.get('upload_date'),
                'chunk_count': len(chunks_data['ids']),
                'metadata': {k: v for k, v in first_chunk_metadata.items() 
                           if k not in ['document_id', 'chunk_index', 'title', 'file_type', 'upload_date', 'category', 'tags']}
            }
            
        except Exception as e:
            logger.error(f"Failed to get document info for {document_id}: {e}")
            return None
    
    def list_documents(
        self, 
        category_filter: Optional[DocumentCategory] = None,
        tags_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List all documents in the knowledge base.
        
        Args:
            category_filter: Filter by document category.
            tags_filter: Filter by document tags.
        
        Returns:
            List of document information dicts.
        """
        try:
            # Build where clause for filtering
            where_clause = {}
            if category_filter:
                where_clause['category'] = category_filter.value
            
            # Get chunks with optional filtering
            if where_clause:
                all_chunks = self.collection.get(where=where_clause)
            else:
                all_chunks = self.collection.get()
            
            # Group by document_id
            documents = {}
            for i, chunk_id in enumerate(all_chunks['ids']):
                metadata = all_chunks['metadatas'][i]
                doc_id = metadata['document_id']
                
                # Apply tags filter if specified
                if tags_filter:
                    doc_tags = metadata.get('tags', [])
                    if isinstance(doc_tags, str):
                        doc_tags = doc_tags.split(',') if doc_tags else []
                    if not any(tag in doc_tags for tag in tags_filter):
                        continue
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        'id': doc_id,
                        'title': metadata.get('title', 'Unknown'),
                        'file_type': metadata.get('file_type', 'unknown'),
                        'category': metadata.get('category', 'general'),
                        'tags': metadata.get('tags', []),
                        'upload_date': metadata.get('upload_date'),
                        'chunk_count': 0,
                        'metadata': {k: v for k, v in metadata.items() 
                                   if k not in ['document_id', 'chunk_index', 'title', 'file_type', 'upload_date', 'category', 'tags']}
                    }
                
                documents[doc_id]['chunk_count'] += 1
            
            return list(documents.values())
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    @with_retry(DATABASE_RETRY_CONFIG, exceptions=(Exception,), logger=logger)
    def search_similar_chunks(
        self, 
        query: str, 
        top_k: int = 5,
        category_filter: Optional[DocumentCategory] = None,
        tags_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar document chunks.
        
        Args:
            query: Search query.
            top_k: Number of top results to return.
            category_filter: Filter by document category.
            tags_filter: Filter by document tags.
            
        Returns:
            List of similar chunks with metadata.
            
        Raises:
            DocumentManagerError: If search fails.
        """
        start_time = time.time()
        
        logger.debug(
            f"Searching for similar chunks: '{query[:50]}...'",
            extra={
                'operation': 'search_similar_chunks',
                'query_length': len(query),
                'top_k': top_k,
                'category_filter': category_filter.value if category_filter else None,
                'tags_filter': tags_filter
            }
        )
        
        # Check cache first
        cache_result = cache_manager.query_cache.get_query_result(
            query, 
            top_k=top_k, 
            category_filter=category_filter, 
            tags_filter=tags_filter
        )
        if cache_result is not None:
            logger.debug("Returning cached search results")
            return cache_result
        
        try:
            # Check embedding cache first
            query_embedding = cache_manager.query_cache.get_embedding(query)
            if query_embedding is None:
                # Generate query embedding using Ollama
                query_embedding = self.ollama_client.generate_embeddings(query)
                # Cache the embedding
                cache_manager.query_cache.cache_embedding(query, query_embedding)
            
            # Build where clause for filtering
            where_clause = {}
            if category_filter:
                where_clause['category'] = category_filter.value
            
            # Search in ChromaDB
            search_params = {
                'query_embeddings': [query_embedding],
                'n_results': top_k * 2,  # Get more results for filtering
                'include': ['documents', 'metadatas', 'distances']
            }
            
            if where_clause:
                search_params['where'] = where_clause
            
            results = self.collection.query(**search_params)
            
            # Format and filter results
            similar_chunks = []
            for i in range(len(results['documents'][0])):
                metadata = results['metadatas'][0][i]
                
                # Apply tags filter if specified
                if tags_filter:
                    doc_tags = metadata.get('tags', [])
                    if isinstance(doc_tags, str):
                        doc_tags = doc_tags.split(',') if doc_tags else []
                    if not any(tag in doc_tags for tag in tags_filter):
                        continue
                
                chunk_data = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': metadata,
                    'distance': results['distances'][0][i],
                    'relevance_score': max(0.0, min(1.0, 1.0 - results['distances'][0][i]))  # Convert distance to similarity, clamp to [0,1]
                }
                similar_chunks.append(chunk_data)
                
                # Stop when we have enough results
                if len(similar_chunks) >= top_k:
                    break
            
            processing_time = time.time() - start_time
            logger.info(
                f"Found {len(similar_chunks)} similar chunks",
                extra={
                    'operation': 'search_similar_chunks',
                    'processing_time': processing_time,
                    'query_length': len(query),
                    'results_count': len(similar_chunks),
                    'top_k': top_k
                }
            )
            
            # Cache the results
            cache_manager.query_cache.cache_query_result(
                query, 
                similar_chunks, 
                ttl=1800,  # 30 minutes
                top_k=top_k, 
                category_filter=category_filter, 
                tags_filter=tags_filter
            )
            
            return similar_chunks
            
        except OllamaConnectionError as e:
            processing_time = time.time() - start_time
            error = handle_error(
                error=e,
                error_code="DOCUMENT_SEARCH_OLLAMA_ERROR",
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.HIGH,
                details={
                    'query_length': len(query),
                    'processing_time': processing_time,
                    'top_k': top_k
                },
                suggestions=[
                    "Check Ollama service status",
                    "Verify embedding model is available",
                    "Try restarting Ollama service"
                ],
                context={'operation': 'search_similar_chunks'}
            )
            raise DocumentManagerError(error.error_info, e)
        except Exception as e:
            processing_time = time.time() - start_time
            error = handle_error(
                error=e,
                error_code="DOCUMENT_SEARCH_FAILED",
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.HIGH,
                details={
                    'query_length': len(query),
                    'processing_time': processing_time,
                    'top_k': top_k,
                    'category_filter': category_filter.value if category_filter else None
                },
                suggestions=[
                    "Check ChromaDB connection",
                    "Verify document collection exists",
                    "Try with a simpler query",
                    "Check available disk space"
                ],
                context={'operation': 'search_similar_chunks'}
            )
            raise DocumentManagerError(error.error_info, e)
    
    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types.
        
        Returns:
            List of supported file extensions.
        """
        return file_processor.get_supported_extensions()
    
    def get_file_type_description(self, file_path: Path) -> str:
        """Get human-readable description of file type.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            File type description.
        """
        return file_processor.get_file_type_description(file_path)
    
    def _store_document_file(self, document: Document, content: str):
        """Store document file in storage directory.
        
        Args:
            document: Document object.
            content: Document content.
        """
        try:
            stored_file_path = self.storage_path / f"{document.id}_{document.file_path.name}"
            
            with open(stored_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update document file path to stored location
            document.file_path = stored_file_path
            
            logger.debug(
                f"Stored document file: {stored_file_path}",
                extra={
                    'operation': 'store_document_file',
                    'document_id': document.id,
                    'stored_path': str(stored_file_path)
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to store document file: {e}",
                extra={
                    'operation': 'store_document_file',
                    'document_id': document.id
                }
            )
            raise

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks (legacy method, use optimized_chunker instead).
        
        Args:
            text: Text to split.
            
        Returns:
            List of text chunks.
        """
        # Use optimized chunker for better performance
        chunks, _ = optimized_chunker.chunk_document(text)
        return chunks
    
    def _store_document_chunks(self, document: Document, chunks: List[str]) -> None:
        """Store document chunks in ChromaDB.
        
        Args:
            document: Document object.
            chunks: List of text chunks.
            
        Raises:
            DocumentManagerError: If storage fails.
        """
        try:
            chunk_ids = []
            chunk_embeddings = []
            chunk_documents = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document.id}_chunk_{i}"
                
                # Generate embedding for chunk
                embedding = self.ollama_client.generate_embeddings(chunk)
                
                # Prepare metadata
                metadata = {
                    'document_id': document.id,
                    'chunk_index': i,
                    'title': document.title,
                    'file_type': document.file_type,
                    'category': document.category.value,
                    'tags': ','.join(document.tags) if document.tags else '',
                    'upload_date': document.created_at.isoformat(),
                    **document.metadata
                }
                
                chunk_ids.append(chunk_id)
                chunk_embeddings.append(embedding)
                chunk_documents.append(chunk)
                chunk_metadatas.append(metadata)
                
                # Update document object
                document.add_chunk(chunk, chunk_id)
            
            # Store in ChromaDB
            self.collection.add(
                ids=chunk_ids,
                embeddings=chunk_embeddings,
                documents=chunk_documents,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Stored {len(chunks)} chunks for document {document.id}")
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error during chunk storage: {e}")
            raise DocumentManagerError(f"Failed to generate embeddings: {e}")
        except Exception as e:
            logger.error(f"Failed to store document chunks: {e}")
            raise DocumentManagerError(f"Chunk storage failed: {e}")
    
    def batch_upload_documents(
        self, 
        file_paths: List[str], 
        common_metadata: Optional[Dict[str, Any]] = None,
        category: DocumentCategory = DocumentCategory.GENERAL,
        tags: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Upload multiple documents in batch.
        
        Args:
            file_paths: List of file paths to upload.
            common_metadata: Common metadata to apply to all documents.
            category: Category to apply to all documents.
            tags: Tags to apply to all documents.
            progress_callback: Optional callback function for progress updates.
            
        Returns:
            List of results for each file upload.
        """
        results = []
        common_metadata = common_metadata or {}
        
        for i, file_path in enumerate(file_paths):
            try:
                # Prepare metadata for this file
                file_metadata = common_metadata.copy()
                file_metadata['batch_upload'] = 'true'
                file_metadata['batch_index'] = str(i)
                
                # Upload document
                doc_id = self.upload_document(
                    file_path=file_path, 
                    metadata=file_metadata,
                    category=category,
                    tags=tags
                )
                
                result = {
                    'success': True,
                    'file_path': file_path,
                    'document_id': doc_id,
                    'error': None
                }
                
            except Exception as e:
                result = {
                    'success': False,
                    'file_path': file_path,
                    'document_id': None,
                    'error': str(e)
                }
                logger.error(f"Failed to upload {file_path} in batch: {e}")
            
            results.append(result)
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, len(file_paths), file_path, result)
        
        return results
    
    def update_document_category(self, document_id: str, category: DocumentCategory) -> bool:
        """Update document category.
        
        Args:
            document_id: ID of document to update.
            category: New category for the document.
            
        Returns:
            True if updated successfully, False otherwise.
        """
        try:
            # Get all chunks for this document
            chunks_data = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not chunks_data['ids']:
                return False
            
            # Update metadata for all chunks
            updated_metadatas = []
            for metadata in chunks_data['metadatas']:
                metadata['category'] = category.value
                updated_metadatas.append(metadata)
            
            # Update in ChromaDB
            self.collection.update(
                ids=chunks_data['ids'],
                metadatas=updated_metadatas
            )
            
            logger.info(f"Updated category for document {document_id} to {category.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document category {document_id}: {e}")
            return False
    
    def update_document_tags(self, document_id: str, tags: List[str]) -> bool:
        """Update document tags.
        
        Args:
            document_id: ID of document to update.
            tags: New tags for the document.
            
        Returns:
            True if updated successfully, False otherwise.
        """
        try:
            # Get all chunks for this document
            chunks_data = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not chunks_data['ids']:
                return False
            
            # Update metadata for all chunks
            updated_metadatas = []
            for metadata in chunks_data['metadatas']:
                metadata['tags'] = ','.join(tags) if tags else ''
                updated_metadatas.append(metadata)
            
            # Update in ChromaDB
            self.collection.update(
                ids=chunks_data['ids'],
                metadatas=updated_metadatas
            )
            
            logger.info(f"Updated tags for document {document_id} to {tags}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document tags {document_id}: {e}")
            return False
    
    def get_reference_documents(self) -> List[Dict[str, Any]]:
        """Get all reference/normative documents.
        
        Returns:
            List of reference documents.
        """
        return self.list_documents(category_filter=DocumentCategory.REFERENCE)
    
    def _health_check(self) -> HealthCheck:
        """Health check for document storage system.
        
        Returns:
            HealthCheck result.
        """
        try:
            start_time = time.time()
            
            # Check ChromaDB connection
            collection_info = self.collection.get(limit=1)
            
            # Check storage directory
            storage_exists = self.storage_path.exists() and self.storage_path.is_dir()
            chroma_exists = self.chroma_path.exists() and self.chroma_path.is_dir()
            
            # Get document count
            all_docs = self.list_documents()
            doc_count = len(all_docs)
            
            # Check disk space
            import shutil
            storage_usage = shutil.disk_usage(self.storage_path)
            storage_free_gb = storage_usage.free / 1024 / 1024 / 1024
            
            response_time = time.time() - start_time
            
            issues = []
            if not storage_exists:
                issues.append("Storage directory not accessible")
            if not chroma_exists:
                issues.append("ChromaDB directory not accessible")
            if storage_free_gb < 1.0:  # Less than 1GB free
                issues.append(f"Low disk space: {storage_free_gb:.1f}GB free")
            
            if issues:
                status = HealthStatus.WARNING if storage_free_gb > 0.1 else HealthStatus.CRITICAL
                message = f"Document storage issues: {'; '.join(issues)}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Document storage healthy with {doc_count} documents"
            
            return HealthCheck(
                name="document_storage",
                status=status,
                message=message,
                details={
                    'document_count': doc_count,
                    'storage_path': str(self.storage_path),
                    'chroma_path': str(self.chroma_path),
                    'storage_free_gb': storage_free_gb,
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheck(
                name="document_storage",
                status=HealthStatus.CRITICAL,
                message=f"Document storage check failed: {e}",
                details={
                    'error': str(e),
                    'error_type': type(e).__name__
                },
                timestamp=datetime.now()
            )
    
    def get_reference_documents(self) -> List[Dict[str, Any]]:
        """Get all reference/normative documents.
        
        Returns:
            List of reference document information.
        """
        return self.list_documents(category_filter=DocumentCategory.REFERENCE)
    
    def search_reference_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks only in reference documents.
        
        Args:
            query: Search query.
            top_k: Number of top results to return.
            
        Returns:
            List of similar chunks from reference documents.
        """
        return self.search_similar_chunks(
            query=query,
            top_k=top_k,
            category_filter=DocumentCategory.REFERENCE
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection.
        
        Returns:
            Collection statistics.
        """
        try:
            collection_data = self.collection.get()
            total_chunks = len(collection_data['ids'])
            
            # Count unique documents and categories
            document_ids = set()
            category_counts = {}
            
            for metadata in collection_data['metadatas']:
                document_ids.add(metadata['document_id'])
                category = metadata.get('category', 'general')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Convert chunk counts to document counts
            documents_by_category = {}
            processed_docs = set()
            
            for metadata in collection_data['metadatas']:
                doc_id = metadata['document_id']
                if doc_id not in processed_docs:
                    category = metadata.get('category', 'general')
                    documents_by_category[category] = documents_by_category.get(category, 0) + 1
                    processed_docs.add(doc_id)
            
            return {
                'total_documents': len(document_ids),
                'total_chunks': total_chunks,
                'average_chunks_per_document': total_chunks / len(document_ids) if document_ids else 0,
                'documents_by_category': documents_by_category,
                'chunks_by_category': category_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {'error': str(e)}
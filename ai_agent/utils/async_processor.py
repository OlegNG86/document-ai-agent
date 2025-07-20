"""Asynchronous document processing for large documents."""

import asyncio
import concurrent.futures
import threading
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import queue

from .logging_config import get_logger
from .performance_monitor import performance_tracker
from .chunk_optimizer import optimized_chunker


logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """Processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingTask:
    """Asynchronous processing task."""
    task_id: str
    file_path: Path
    content: str
    metadata: Dict[str, Any]
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class AsyncDocumentProcessor:
    """Asynchronous document processor for large documents."""
    
    def __init__(self, max_workers: int = 4, large_doc_threshold: int = 50000):
        """Initialize async processor.
        
        Args:
            max_workers: Maximum number of worker threads.
            large_doc_threshold: Threshold in characters for large documents.
        """
        self.max_workers = max_workers
        self.large_doc_threshold = large_doc_threshold
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, ProcessingTask] = {}
        self.task_queue = queue.Queue()
        self.progress_callbacks: Dict[str, Callable] = {}
        
        # Start worker threads
        self.workers_active = True
        self.worker_threads = []
        for i in range(max_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        logger.info(f"Async document processor started with {max_workers} workers")
    
    def should_process_async(self, content: str) -> bool:
        """Check if document should be processed asynchronously.
        
        Args:
            content: Document content.
            
        Returns:
            True if should process async.
        """
        return len(content) > self.large_doc_threshold
    
    def submit_task(self, task_id: str, file_path: Path, content: str, 
                   metadata: Optional[Dict[str, Any]] = None,
                   progress_callback: Optional[Callable] = None) -> ProcessingTask:
        """Submit document processing task.
        
        Args:
            task_id: Unique task identifier.
            file_path: Path to document file.
            content: Document content.
            metadata: Optional metadata.
            progress_callback: Optional progress callback function.
            
        Returns:
            Processing task.
        """
        task = ProcessingTask(
            task_id=task_id,
            file_path=file_path,
            content=content,
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        if progress_callback:
            self.progress_callbacks[task_id] = progress_callback
        
        # Add to queue
        self.task_queue.put(task)
        
        logger.info(
            f"Submitted async processing task: {task_id}",
            extra={
                'operation': 'submit_async_task',
                'task_id': task_id,
                'content_length': len(content),
                'file_path': str(file_path)
            }
        )
        
        return task
    
    def get_task_status(self, task_id: str) -> Optional[ProcessingTask]:
        """Get task status.
        
        Args:
            task_id: Task identifier.
            
        Returns:
            Task status or None if not found.
        """
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel processing task.
        
        Args:
            task_id: Task identifier.
            
        Returns:
            True if cancelled successfully.
        """
        task = self.tasks.get(task_id)
        if task and task.status == ProcessingStatus.PENDING:
            task.status = ProcessingStatus.CANCELLED
            logger.info(f"Cancelled task: {task_id}")
            return True
        return False
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """Wait for task completion.
        
        Args:
            task_id: Task identifier.
            timeout: Optional timeout in seconds.
            
        Returns:
            Task result or None if timeout/error.
        """
        start_time = time.time()
        
        while True:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            if task.status == ProcessingStatus.COMPLETED:
                return task.result
            elif task.status in [ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                return None
            
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Task {task_id} timed out after {timeout}s")
                return None
            
            time.sleep(0.1)
    
    def _worker_loop(self, worker_id: int):
        """Worker thread loop.
        
        Args:
            worker_id: Worker identifier.
        """
        logger.debug(f"Worker {worker_id} started")
        
        while self.workers_active:
            try:
                # Get task from queue with timeout
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if task.status == ProcessingStatus.CANCELLED:
                    continue
                
                # Process task
                self._process_task(task, worker_id)
                
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
                time.sleep(1)
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def _process_task(self, task: ProcessingTask, worker_id: int):
        """Process a single task.
        
        Args:
            task: Processing task.
            worker_id: Worker identifier.
        """
        task.status = ProcessingStatus.PROCESSING
        task.started_at = time.time()
        
        logger.info(
            f"Worker {worker_id} processing task: {task.task_id}",
            extra={
                'operation': 'process_async_task',
                'task_id': task.task_id,
                'worker_id': worker_id,
                'content_length': len(task.content)
            }
        )
        
        try:
            with performance_tracker(f"async_process_document_{task.task_id}"):
                # Process document in chunks
                result = self._process_document_chunks(task)
                
                task.result = result
                task.status = ProcessingStatus.COMPLETED
                task.progress = 100.0
                task.completed_at = time.time()
                
                processing_time = task.completed_at - task.started_at
                logger.info(
                    f"Task {task.task_id} completed in {processing_time:.2f}s",
                    extra={
                        'operation': 'async_task_completed',
                        'task_id': task.task_id,
                        'processing_time': processing_time,
                        'worker_id': worker_id
                    }
                )
                
                # Call progress callback
                if task.task_id in self.progress_callbacks:
                    try:
                        self.progress_callbacks[task.task_id](task)
                    except Exception as e:
                        logger.error(f"Error in progress callback for {task.task_id}: {e}")
        
        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            
            logger.error(
                f"Task {task.task_id} failed: {e}",
                extra={
                    'operation': 'async_task_failed',
                    'task_id': task.task_id,
                    'error': str(e),
                    'worker_id': worker_id
                }
            )
    
    def _process_document_chunks(self, task: ProcessingTask) -> Dict[str, Any]:
        """Process document by chunking and parallel processing.
        
        Args:
            task: Processing task.
            
        Returns:
            Processing result.
        """
        # Update progress
        task.progress = 10.0
        
        # Chunk document optimally
        chunks, chunk_metadata = optimized_chunker.chunk_document(
            task.content, 
            str(task.file_path.name)
        )
        
        task.progress = 30.0
        
        # Process chunks in parallel
        chunk_results = []
        total_chunks = len(chunks)
        
        # Use smaller thread pool for chunk processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, total_chunks)) as chunk_executor:
            # Submit chunk processing tasks
            future_to_chunk = {
                chunk_executor.submit(self._process_single_chunk, i, chunk, task.metadata): i
                for i, chunk in enumerate(chunks)
            }
            
            completed_chunks = 0
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_idx = future_to_chunk[future]
                try:
                    chunk_result = future.result()
                    chunk_results.append((chunk_idx, chunk_result))
                    
                    completed_chunks += 1
                    # Update progress (30% to 90%)
                    task.progress = 30.0 + (completed_chunks / total_chunks) * 60.0
                    
                except Exception as e:
                    logger.error(f"Chunk {chunk_idx} processing failed: {e}")
                    chunk_results.append((chunk_idx, None))
        
        # Sort results by chunk index
        chunk_results.sort(key=lambda x: x[0])
        processed_chunks = [result for _, result in chunk_results if result is not None]
        
        task.progress = 95.0
        
        # Combine results
        result = {
            'chunks': processed_chunks,
            'chunk_metadata': chunk_metadata,
            'total_chunks': len(chunks),
            'successful_chunks': len(processed_chunks),
            'failed_chunks': len(chunks) - len(processed_chunks),
            'processing_time': time.time() - task.started_at if task.started_at else 0
        }
        
        return result
    
    def _process_single_chunk(self, chunk_idx: int, chunk_content: str, 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single chunk.
        
        Args:
            chunk_idx: Chunk index.
            chunk_content: Chunk content.
            metadata: Processing metadata.
            
        Returns:
            Chunk processing result.
        """
        # Simulate chunk processing (in real implementation, this would generate embeddings, etc.)
        start_time = time.time()
        
        # Basic processing
        word_count = len(chunk_content.split())
        char_count = len(chunk_content)
        
        # Simulate some processing time based on chunk size
        processing_time = min(0.1 + (char_count / 10000), 2.0)
        time.sleep(processing_time)
        
        result = {
            'chunk_index': chunk_idx,
            'content': chunk_content,
            'word_count': word_count,
            'char_count': char_count,
            'processing_time': time.time() - start_time,
            'metadata': metadata
        }
        
        return result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.
        
        Returns:
            Processing statistics.
        """
        total_tasks = len(self.tasks)
        status_counts = {}
        
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate average processing time for completed tasks
        completed_tasks = [t for t in self.tasks.values() if t.status == ProcessingStatus.COMPLETED]
        avg_processing_time = 0.0
        if completed_tasks:
            total_time = sum(
                (t.completed_at - t.started_at) for t in completed_tasks 
                if t.started_at and t.completed_at
            )
            avg_processing_time = total_time / len(completed_tasks)
        
        return {
            'total_tasks': total_tasks,
            'status_counts': status_counts,
            'queue_size': self.task_queue.qsize(),
            'active_workers': len([t for t in self.worker_threads if t.is_alive()]),
            'max_workers': self.max_workers,
            'avg_processing_time': avg_processing_time,
            'large_doc_threshold': self.large_doc_threshold
        }
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks.
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks.
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED] and
                task.completed_at and (current_time - task.completed_at) > max_age_seconds):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            if task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def shutdown(self, timeout: float = 30.0):
        """Shutdown async processor.
        
        Args:
            timeout: Shutdown timeout in seconds.
        """
        logger.info("Shutting down async document processor...")
        
        # Stop workers
        self.workers_active = False
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=timeout / len(self.worker_threads))
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=timeout)
        
        logger.info("Async document processor shut down")


# Global async processor instance
async_processor = AsyncDocumentProcessor()
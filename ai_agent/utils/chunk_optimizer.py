"""Optimized text chunking for different document types."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .logging_config import get_logger


logger = get_logger(__name__)


class DocumentType(Enum):
    """Document type classification."""
    LEGAL = "legal"
    TECHNICAL = "technical"
    NARRATIVE = "narrative"
    STRUCTURED = "structured"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int
    chunk_overlap: int
    sentence_boundary: bool = True
    paragraph_boundary: bool = True
    preserve_structure: bool = False
    min_chunk_size: int = 100
    max_chunk_size: Optional[int] = None


class DocumentClassifier:
    """Classify documents to determine optimal chunking strategy."""
    
    def __init__(self):
        """Initialize document classifier."""
        # Legal document patterns
        self.legal_patterns = [
            r'\b(статья|пункт|подпункт|глава|раздел)\s+\d+',
            r'\b(закон|кодекс|постановление|приказ|регламент)',
            r'\b(договор|контракт|соглашение|протокол)',
            r'\b(требования|обязательства|ответственность)',
            r'\b(в соответствии с|согласно|на основании)'
        ]
        
        # Technical document patterns
        self.technical_patterns = [
            r'\b(технические требования|спецификация|стандарт)',
            r'\b(параметры|характеристики|показатели)',
            r'\b(методика|процедура|алгоритм)',
            r'\b(система|устройство|оборудование)',
            r'\b(ГОСТ|ТУ|СНиП|СП)\s*\d+'
        ]
        
        # Structured document patterns
        self.structured_patterns = [
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[а-я]\)\s+',  # Lettered lists
            r'^\s*[-•]\s+',  # Bullet points
            r'^\s*#{1,6}\s+',  # Markdown headers
            r'^\s*\|\s*.*\s*\|',  # Tables
        ]
    
    def classify_document(self, content: str, filename: Optional[str] = None) -> DocumentType:
        """Classify document type based on content and filename.
        
        Args:
            content: Document content.
            filename: Optional filename.
            
        Returns:
            Classified document type.
        """
        content_lower = content.lower()
        
        # Count pattern matches
        legal_score = sum(len(re.findall(pattern, content_lower, re.IGNORECASE)) 
                         for pattern in self.legal_patterns)
        
        technical_score = sum(len(re.findall(pattern, content_lower, re.IGNORECASE)) 
                             for pattern in self.technical_patterns)
        
        structured_score = sum(len(re.findall(pattern, content, re.MULTILINE)) 
                              for pattern in self.structured_patterns)
        
        # Normalize scores by content length
        content_length = len(content.split())
        if content_length > 0:
            legal_score = legal_score / content_length * 1000
            technical_score = technical_score / content_length * 1000
            structured_score = structured_score / content_length * 1000
        
        # Check filename hints
        filename_hints = {}
        if filename:
            filename_lower = filename.lower()
            if any(word in filename_lower for word in ['закон', 'договор', 'контракт', 'регламент']):
                filename_hints[DocumentType.LEGAL] = 2.0
            elif any(word in filename_lower for word in ['техн', 'спец', 'гост', 'стандарт']):
                filename_hints[DocumentType.TECHNICAL] = 2.0
        
        # Determine document type
        scores = {
            DocumentType.LEGAL: legal_score + filename_hints.get(DocumentType.LEGAL, 0),
            DocumentType.TECHNICAL: technical_score + filename_hints.get(DocumentType.TECHNICAL, 0),
            DocumentType.STRUCTURED: structured_score
        }
        
        # Check for mixed content
        high_scores = [doc_type for doc_type, score in scores.items() if score > 1.0]
        if len(high_scores) > 1:
            return DocumentType.MIXED
        
        # Return highest scoring type
        max_type = max(scores.items(), key=lambda x: x[1])
        if max_type[1] > 0.5:
            return max_type[0]
        
        # Check if it's narrative (long paragraphs, few lists)
        paragraphs = content.split('\n\n')
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        if avg_paragraph_length > 50 and structured_score < 0.1:
            return DocumentType.NARRATIVE
        
        return DocumentType.UNKNOWN


class OptimizedChunker:
    """Optimized text chunker with document type awareness."""
    
    def __init__(self):
        """Initialize optimized chunker."""
        self.classifier = DocumentClassifier()
        
        # Default configurations for different document types
        self.chunk_configs = {
            DocumentType.LEGAL: ChunkConfig(
                chunk_size=800,  # Smaller chunks for precise legal references
                chunk_overlap=150,
                sentence_boundary=True,
                paragraph_boundary=True,
                preserve_structure=True
            ),
            DocumentType.TECHNICAL: ChunkConfig(
                chunk_size=1200,  # Larger chunks for technical context
                chunk_overlap=200,
                sentence_boundary=True,
                paragraph_boundary=True,
                preserve_structure=True
            ),
            DocumentType.NARRATIVE: ChunkConfig(
                chunk_size=1000,  # Standard chunks for narrative text
                chunk_overlap=200,
                sentence_boundary=True,
                paragraph_boundary=False
            ),
            DocumentType.STRUCTURED: ChunkConfig(
                chunk_size=600,  # Smaller chunks to preserve list structure
                chunk_overlap=100,
                sentence_boundary=False,
                paragraph_boundary=True,
                preserve_structure=True
            ),
            DocumentType.MIXED: ChunkConfig(
                chunk_size=900,  # Balanced approach for mixed content
                chunk_overlap=180,
                sentence_boundary=True,
                paragraph_boundary=True,
                preserve_structure=True
            ),
            DocumentType.UNKNOWN: ChunkConfig(
                chunk_size=1000,  # Default configuration
                chunk_overlap=200,
                sentence_boundary=True,
                paragraph_boundary=True
            )
        }
    
    def chunk_document(self, content: str, filename: Optional[str] = None, 
                      custom_config: Optional[ChunkConfig] = None) -> Tuple[List[str], Dict[str, Any]]:
        """Chunk document with optimized strategy.
        
        Args:
            content: Document content.
            filename: Optional filename for classification hints.
            custom_config: Optional custom chunking configuration.
            
        Returns:
            Tuple of (chunks, metadata).
        """
        # Classify document type
        doc_type = self.classifier.classify_document(content, filename)
        
        # Get chunking configuration
        config = custom_config or self.chunk_configs[doc_type]
        
        logger.debug(
            f"Chunking document as {doc_type.value}",
            extra={
                'operation': 'chunk_document',
                'document_type': doc_type.value,
                'chunk_size': config.chunk_size,
                'chunk_overlap': config.chunk_overlap,
                'content_length': len(content)
            }
        )
        
        # Apply chunking strategy based on document type
        if doc_type == DocumentType.STRUCTURED:
            chunks = self._chunk_structured_document(content, config)
        elif doc_type == DocumentType.LEGAL:
            chunks = self._chunk_legal_document(content, config)
        elif doc_type == DocumentType.TECHNICAL:
            chunks = self._chunk_technical_document(content, config)
        else:
            chunks = self._chunk_standard_document(content, config)
        
        # Filter out too small chunks
        chunks = [chunk for chunk in chunks if len(chunk.strip()) >= config.min_chunk_size]
        
        # Apply max chunk size if specified
        if config.max_chunk_size:
            chunks = [chunk[:config.max_chunk_size] if len(chunk) > config.max_chunk_size else chunk 
                     for chunk in chunks]
        
        metadata = {
            'document_type': doc_type.value,
            'chunk_count': len(chunks),
            'chunk_size': config.chunk_size,
            'chunk_overlap': config.chunk_overlap,
            'avg_chunk_length': sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
            'min_chunk_length': min(len(chunk) for chunk in chunks) if chunks else 0,
            'max_chunk_length': max(len(chunk) for chunk in chunks) if chunks else 0
        }
        
        logger.info(
            f"Document chunked into {len(chunks)} chunks",
            extra={
                'operation': 'chunk_document',
                'document_type': doc_type.value,
                'chunk_count': len(chunks),
                'avg_chunk_length': metadata['avg_chunk_length']
            }
        )
        
        return chunks, metadata
    
    def _chunk_structured_document(self, content: str, config: ChunkConfig) -> List[str]:
        """Chunk structured document preserving list structure."""
        chunks = []
        current_chunk = ""
        
        lines = content.split('\n')
        
        for line in lines:
            # Check if line starts a new structure (numbered list, bullet, etc.)
            is_structure_start = any(re.match(pattern, line) for pattern in [
                r'^\s*\d+\.\s+',
                r'^\s*[а-я]\)\s+',
                r'^\s*[-•]\s+',
                r'^\s*#{1,6}\s+'
            ])
            
            # If adding this line would exceed chunk size and we have content
            if (len(current_chunk) + len(line) > config.chunk_size and 
                current_chunk.strip() and is_structure_start):
                
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
            else:
                current_chunk += line + '\n'
        
        # Add remaining content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return self._apply_overlap(chunks, config.chunk_overlap)
    
    def _chunk_legal_document(self, content: str, config: ChunkConfig) -> List[str]:
        """Chunk legal document preserving article/section structure."""
        chunks = []
        current_chunk = ""
        
        # Split by legal structure markers
        sections = re.split(r'(\b(?:статья|пункт|подпункт|глава|раздел)\s+\d+)', content, flags=re.IGNORECASE)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # If this is a section header, start new chunk if current is large enough
            if (i % 2 == 1 and len(current_chunk) > config.chunk_size // 2):
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = section + ' '
            else:
                current_chunk += section
                
                # Check if chunk is getting too large
                if len(current_chunk) > config.chunk_size:
                    # Try to split at sentence boundary
                    sentences = re.split(r'(?<=[.!?])\s+', current_chunk)
                    if len(sentences) > 1:
                        # Keep sentences until we exceed size
                        chunk_sentences = []
                        remaining_sentences = []
                        current_size = 0
                        
                        for sentence in sentences:
                            if current_size + len(sentence) <= config.chunk_size or not chunk_sentences:
                                chunk_sentences.append(sentence)
                                current_size += len(sentence)
                            else:
                                remaining_sentences.append(sentence)
                        
                        if chunk_sentences:
                            chunks.append(' '.join(chunk_sentences))
                        current_chunk = ' '.join(remaining_sentences)
        
        # Add remaining content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return self._apply_overlap(chunks, config.chunk_overlap)
    
    def _chunk_technical_document(self, content: str, config: ChunkConfig) -> List[str]:
        """Chunk technical document preserving technical sections."""
        # Use standard chunking but with larger chunks for technical context
        return self._chunk_standard_document(content, config)
    
    def _chunk_standard_document(self, content: str, config: ChunkConfig) -> List[str]:
        """Standard document chunking with sentence/paragraph boundaries."""
        if len(content) <= config.chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + config.chunk_size
            
            if end >= len(content):
                chunks.append(content[start:])
                break
            
            # Try to find good boundary
            chunk_text = content[start:end]
            boundary_pos = -1
            
            if config.paragraph_boundary:
                # Look for paragraph boundary
                boundary_pos = chunk_text.rfind('\n\n')
                if boundary_pos < config.chunk_size // 3:  # Too close to start
                    boundary_pos = -1
            
            if boundary_pos == -1 and config.sentence_boundary:
                # Look for sentence boundary
                for punct in ['. ', '! ', '? ']:
                    pos = chunk_text.rfind(punct)
                    if pos > config.chunk_size // 2:  # Good position
                        boundary_pos = pos + len(punct) - 1
                        break
            
            if boundary_pos == -1:
                # Look for word boundary
                boundary_pos = chunk_text.rfind(' ')
                if boundary_pos < config.chunk_size // 2:
                    boundary_pos = config.chunk_size
            
            actual_end = start + boundary_pos + 1 if boundary_pos != -1 else end
            chunks.append(content[start:actual_end])
            
            # Move start position with overlap
            start = actual_end - config.chunk_overlap
            if start < 0:
                start = actual_end
        
        return chunks
    
    def _apply_overlap(self, chunks: List[str], overlap_size: int) -> List[str]:
        """Apply overlap between chunks."""
        if len(chunks) <= 1 or overlap_size <= 0:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            current_chunk = chunks[i]
            
            # Get overlap from previous chunk
            overlap_text = prev_chunk[-overlap_size:] if len(prev_chunk) > overlap_size else prev_chunk
            
            # Add overlap to current chunk if it doesn't already contain it
            if not current_chunk.startswith(overlap_text.strip()):
                overlapped_chunk = overlap_text + ' ' + current_chunk
            else:
                overlapped_chunk = current_chunk
            
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
    
    def get_optimal_config(self, doc_type: DocumentType) -> ChunkConfig:
        """Get optimal chunking configuration for document type.
        
        Args:
            doc_type: Document type.
            
        Returns:
            Optimal chunking configuration.
        """
        return self.chunk_configs.get(doc_type, self.chunk_configs[DocumentType.UNKNOWN])
    
    def update_config(self, doc_type: DocumentType, config: ChunkConfig):
        """Update chunking configuration for document type.
        
        Args:
            doc_type: Document type.
            config: New configuration.
        """
        self.chunk_configs[doc_type] = config
        logger.info(f"Updated chunking config for {doc_type.value}")


# Global optimized chunker instance
optimized_chunker = OptimizedChunker()
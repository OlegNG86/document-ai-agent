"""Caching system for performance optimization."""

import time
import hashlib
import pickle
import threading
from typing import Any, Optional, Dict, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from pathlib import Path

from .logging_config import get_logger
from .performance_monitor import performance_tracker


logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries.
            default_ttl: Default TTL in seconds.
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0,
            'total_size_bytes': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key.
            
        Returns:
            Cached value or None if not found/expired.
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                self._stats['total_size_bytes'] -= entry.size_bytes
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            self._stats['hits'] += 1
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in cache.
        
        Args:
            key: Cache key.
            value: Value to cache.
            ttl: TTL in seconds, uses default if None.
        """
        with self._lock:
            # Calculate size
            try:
                size_bytes = len(pickle.dumps(value))
            except Exception:
                size_bytes = 0
            
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats['total_size_bytes'] -= old_entry.size_bytes
                del self._cache[key]
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl_seconds=ttl or self.default_ttl,
                size_bytes=size_bytes
            )
            
            # Add to cache
            self._cache[key] = entry
            self._stats['total_size_bytes'] += size_bytes
            
            # Evict if necessary
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                oldest_entry = self._cache[oldest_key]
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
                self._stats['total_size_bytes'] -= oldest_entry.size_bytes
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache.
        
        Args:
            key: Cache key.
            
        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._stats['total_size_bytes'] -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired': 0,
                'total_size_bytes': 0
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of expired entries removed.
        """
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['total_size_bytes'] -= entry.size_bytes
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics dictionary.
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired'],
                'total_size_mb': self._stats['total_size_bytes'] / 1024 / 1024
            }


class QueryCache:
    """Specialized cache for query results."""
    
    def __init__(self, max_size: int = 500, default_ttl: int = 3600):
        """Initialize query cache.
        
        Args:
            max_size: Maximum number of cached queries.
            default_ttl: Default TTL in seconds (1 hour).
        """
        self.cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        self.embedding_cache = LRUCache(max_size=1000, default_ttl=7200)  # 2 hours
    
    def _generate_query_key(self, query: str, **kwargs) -> str:
        """Generate cache key for query.
        
        Args:
            query: Query text.
            **kwargs: Additional parameters.
            
        Returns:
            Cache key.
        """
        # Include relevant parameters in key
        key_data = {
            'query': query.lower().strip(),
            'top_k': kwargs.get('top_k', 5),
            'category_filter': kwargs.get('category_filter'),
            'tags_filter': sorted(kwargs.get('tags_filter', []) or [])
        }
        
        key_str = str(sorted(key_data.items()))
        try:
            return hashlib.md5(key_str.encode('utf-8')).hexdigest()
        except UnicodeEncodeError:
            return hashlib.md5(key_str.encode('utf-8', errors='ignore')).hexdigest()
    
    def _generate_embedding_key(self, text: str, model: str = "nomic-embed-text") -> str:
        """Generate cache key for embeddings.
        
        Args:
            text: Text to embed.
            model: Embedding model.
            
        Returns:
            Cache key.
        """
        # Clean text from surrogate characters and other problematic Unicode
        try:
            # Remove surrogate characters and other problematic Unicode
            clean_text = text.encode('utf-8', errors='ignore').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Fallback: replace problematic characters
            clean_text = ''.join(char for char in text if ord(char) < 0x110000 and not (0xD800 <= ord(char) <= 0xDFFF))
        
        key_str = f"{model}:{clean_text}"
        try:
            return hashlib.md5(key_str.encode('utf-8')).hexdigest()
        except UnicodeEncodeError:
            # Final fallback: use ASCII encoding with replacement
            return hashlib.md5(key_str.encode('ascii', errors='replace')).hexdigest()
    
    def get_query_result(self, query: str, **kwargs) -> Optional[Any]:
        """Get cached query result.
        
        Args:
            query: Query text.
            **kwargs: Query parameters.
            
        Returns:
            Cached result or None.
        """
        key = self._generate_query_key(query, **kwargs)
        result = self.cache.get(key)
        
        if result is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
        
        return result
    
    def cache_query_result(self, query: str, result: Any, ttl: Optional[int] = None, **kwargs) -> None:
        """Cache query result.
        
        Args:
            query: Query text.
            result: Query result.
            ttl: TTL in seconds.
            **kwargs: Query parameters.
        """
        key = self._generate_query_key(query, **kwargs)
        self.cache.put(key, result, ttl)
        
        logger.debug(f"Cached query result: {query[:50]}...")
    
    def get_embedding(self, text: str, model: str = "nomic-embed-text") -> Optional[list]:
        """Get cached embedding.
        
        Args:
            text: Text to embed.
            model: Embedding model.
            
        Returns:
            Cached embedding or None.
        """
        key = self._generate_embedding_key(text, model)
        result = self.embedding_cache.get(key)
        
        if result is not None:
            logger.debug(f"Embedding cache hit for text: {text[:50]}...")
        
        return result
    
    def cache_embedding(self, text: str, embedding: list, model: str = "nomic-embed-text", 
                       ttl: Optional[int] = None) -> None:
        """Cache embedding.
        
        Args:
            text: Text that was embedded.
            embedding: Embedding vector.
            model: Embedding model.
            ttl: TTL in seconds.
        """
        key = self._generate_embedding_key(text, model)
        self.embedding_cache.put(key, embedding, ttl)
        
        logger.debug(f"Cached embedding for text: {text[:50]}...")
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.cache.clear()
        self.embedding_cache.clear()
        logger.info("All caches cleared")
    
    def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired entries.
        
        Returns:
            Cleanup statistics.
        """
        query_expired = self.cache.cleanup_expired()
        embedding_expired = self.embedding_cache.cleanup_expired()
        
        total_expired = query_expired + embedding_expired
        if total_expired > 0:
            logger.info(f"Cleaned up {total_expired} expired cache entries")
        
        return {
            'query_expired': query_expired,
            'embedding_expired': embedding_expired,
            'total_expired': total_expired
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics.
        """
        return {
            'query_cache': self.cache.get_stats(),
            'embedding_cache': self.embedding_cache.get_stats()
        }


class CacheManager:
    """Global cache manager."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.query_cache = QueryCache()
        self._cleanup_thread = None
        self._cleanup_active = False
        
        # Start cleanup thread
        self.start_cleanup_thread()
    
    def start_cleanup_thread(self):
        """Start background cleanup thread."""
        if self._cleanup_active:
            return
        
        self._cleanup_active = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
    def stop_cleanup_thread(self):
        """Stop background cleanup thread."""
        self._cleanup_active = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Cache cleanup thread stopped")
    
    def _cleanup_loop(self):
        """Background cleanup loop."""
        while self._cleanup_active:
            try:
                # Clean up expired entries every 5 minutes
                time.sleep(300)
                if self._cleanup_active:
                    self.query_cache.cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
                time.sleep(60)
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global cache statistics.
        
        Returns:
            Global cache statistics.
        """
        return {
            'query_cache_stats': self.query_cache.get_stats(),
            'cleanup_active': self._cleanup_active
        }
    
    def clear_all_caches(self):
        """Clear all caches."""
        self.query_cache.clear_all()
        logger.info("All caches cleared globally")


# Global cache manager instance
cache_manager = CacheManager()


def cached_query(ttl: Optional[int] = None):
    """Decorator for caching query results.
    
    Args:
        ttl: TTL in seconds.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            try:
                cache_key = hashlib.md5(cache_key.encode('utf-8')).hexdigest()
            except UnicodeEncodeError:
                cache_key = hashlib.md5(cache_key.encode('utf-8', errors='ignore')).hexdigest()
            
            # Try to get from cache
            result = cache_manager.query_cache.cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            with performance_tracker(f"cached_{func.__name__}"):
                result = func(*args, **kwargs)
                cache_manager.query_cache.cache.put(cache_key, result, ttl)
                return result
        
        return wrapper
    return decorator
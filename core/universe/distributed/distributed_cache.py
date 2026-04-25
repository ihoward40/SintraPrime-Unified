"""
Distributed Cache - Redis integration with cache invalidation and warming

Provides:
- Redis integration
- Cache invalidation
- TTL management
- Batch operations
- Cache warming
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL_ONLY = "ttl"  # Time based only


@dataclass
class CacheEntry:
    """Entry in the distributed cache."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    tags: Set[str] = field(default_factory=set)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    def is_recently_accessed(self, time_window_s: int = 300) -> bool:
        """Check if entry was recently accessed."""
        return (time.time() - self.last_accessed_at) < time_window_s

    def update_access(self) -> None:
        """Update access metadata."""
        self.last_accessed_at = time.time()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_entries: int = 0
    memory_bytes: int = 0

    def get_hit_ratio(self) -> float:
        """Get cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_hit_ratio_percent(self) -> float:
        """Get hit ratio as percentage."""
        return self.get_hit_ratio() * 100


class DistributedCache:
    """Distributed cache with Redis-like interface and advanced features."""

    def __init__(
        self,
        max_size: int = 10000,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl_seconds: Optional[int] = None
    ):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.strategy = strategy
        self.default_ttl_seconds = default_ttl_seconds
        self.key_by_tag: Dict[str, Set[str]] = defaultdict(set)
        self.stats = CacheStatistics()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            self.stats.misses += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            self._evict_entry(key)
            self.stats.misses += 1
            return None

        entry.update_access()
        self.stats.hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in cache."""
        # Use default TTL if not specified
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl_seconds

        # Evict if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_lru() if self.strategy == CacheStrategy.LRU else self._evict_lfu()

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            tags=tags or set()
        )

        # Update tag index
        old_entry = self.cache.get(key)
        if old_entry:
            for tag in old_entry.tags:
                self.key_by_tag[tag].discard(key)

        self.cache[key] = entry
        for tag in entry.tags:
            self.key_by_tag[tag].add(key)

        self.stats.total_entries = len(self.cache)
        return True

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key not in self.cache:
            return False

        entry = self.cache[key]
        for tag in entry.tags:
            self.key_by_tag[tag].discard(key)

        del self.cache[key]
        self.stats.total_entries = len(self.cache)
        return True

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.key_by_tag.clear()
        self.stats.total_entries = 0

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        keys_to_remove = list(self.key_by_tag.get(tag, set()))
        for key in keys_to_remove:
            self.delete(key)
            self.stats.invalidations += 1

        return len(keys_to_remove)

    def invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate entries matching a pattern."""
        import fnmatch

        keys_to_remove = [
            key for key in self.cache.keys()
            if fnmatch.fnmatch(key, pattern)
        ]

        for key in keys_to_remove:
            self.delete(key)
            self.stats.invalidations += 1

        return len(keys_to_remove)

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(
        self,
        items: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> int:
        """Set multiple values in cache."""
        count = 0
        for key, value in items.items():
            if self.set(key, value, ttl_seconds):
                count += 1
        return count

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment integer value."""
        value = self.get(key)
        if value is None:
            new_value = amount
        else:
            new_value = int(value) + amount

        self.set(key, new_value)
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement integer value."""
        return self.incr(key, -amount)

    def append(self, key: str, suffix: str) -> int:
        """Append to string value."""
        value = self.get(key)
        if value is None:
            new_value = suffix
        else:
            new_value = str(value) + suffix

        self.set(key, new_value)
        return len(str(new_value))

    def lpush(self, key: str, *values: Any) -> int:
        """Push values to left of list."""
        current_list = self.get(key)
        if current_list is None:
            current_list = []
        elif not isinstance(current_list, list):
            return -1

        # Insert all values at the beginning (each new value becomes the new head)
        for value in values:
            current_list.insert(0, value)

        self.set(key, current_list)
        return len(current_list)

    def rpush(self, key: str, *values: Any) -> int:
        """Push values to right of list."""
        current_list = self.get(key)
        if current_list is None:
            current_list = []
        elif not isinstance(current_list, list):
            return -1

        current_list.extend(values)
        self.set(key, current_list)
        return len(current_list)

    def lpop(self, key: str, count: int = 1) -> Any:
        """Pop from left of list."""
        current_list = self.get(key)
        if current_list is None or not isinstance(current_list, list):
            return None

        if count == 1:
            if len(current_list) > 0:
                result = current_list.pop(0)
                self.set(key, current_list)
                return result
        else:
            result = current_list[:count]
            current_list = current_list[count:]
            self.set(key, current_list)
            return result

        return None

    def rpop(self, key: str, count: int = 1) -> Any:
        """Pop from right of list."""
        current_list = self.get(key)
        if current_list is None or not isinstance(current_list, list):
            return None

        if count == 1:
            if len(current_list) > 0:
                result = current_list.pop()
                self.set(key, current_list)
                return result
        else:
            result = current_list[-count:]
            current_list = current_list[:-count]
            self.set(key, current_list)
            return result

        return None

    def llen(self, key: str) -> int:
        """Get length of list."""
        current_list = self.get(key)
        if not isinstance(current_list, list):
            return 0
        return len(current_list)

    def sadd(self, key: str, *members: Any) -> int:
        """Add members to set."""
        current_set = self.get(key)
        if current_set is None:
            current_set = set()
        elif not isinstance(current_set, set):
            return -1

        added_count = 0
        for member in members:
            if member not in current_set:
                current_set.add(member)
                added_count += 1

        self.set(key, current_set)
        return added_count

    def srem(self, key: str, *members: Any) -> int:
        """Remove members from set."""
        current_set = self.get(key)
        if current_set is None or not isinstance(current_set, set):
            return 0

        removed_count = 0
        for member in members:
            if member in current_set:
                current_set.discard(member)
                removed_count += 1

        self.set(key, current_set)
        return removed_count

    def scard(self, key: str) -> int:
        """Get set cardinality."""
        current_set = self.get(key)
        if not isinstance(current_set, set):
            return 0
        return len(current_set)

    def hset(self, key: str, field: str, value: Any) -> int:
        """Set hash field."""
        current_hash = self.get(key)
        if current_hash is None:
            current_hash = {}
        elif not isinstance(current_hash, dict):
            return -1

        is_new = field not in current_hash
        current_hash[field] = value
        self.set(key, current_hash)
        return 1 if is_new else 0

    def hget(self, key: str, field: str) -> Any:
        """Get hash field."""
        current_hash = self.get(key)
        if not isinstance(current_hash, dict):
            return None
        return current_hash.get(field)

    def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        current_hash = self.get(key)
        if not isinstance(current_hash, dict):
            return 0

        deleted_count = 0
        for field in fields:
            if field in current_hash:
                del current_hash[field]
                deleted_count += 1

        self.set(key, current_hash)
        return deleted_count

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed_at
        )
        self._evict_entry(lru_key)

    def _evict_lfu(self) -> None:
        """Evict least frequently used entry."""
        if not self.cache:
            return

        lfu_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].access_count
        )
        self._evict_entry(lfu_key)

    def _evict_entry(self, key: str) -> None:
        """Evict an entry from cache."""
        if key in self.cache:
            entry = self.cache[key]
            for tag in entry.tags:
                self.key_by_tag[tag].discard(key)
            del self.cache[key]
            self.stats.evictions += 1
            self.stats.total_entries = len(self.cache)

    def warm_cache(self, data: Dict[str, Tuple[Any, Optional[int]]]) -> int:
        """Warm cache with initial data."""
        count = 0
        for key, (value, ttl) in data.items():
            if self.set(key, value, ttl):
                count += 1
        logger.info(f"Cache warmed with {count} entries")
        return count

    def cleanup_expired_entries(self) -> int:
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            self._evict_entry(key)

        return len(expired_keys)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self.cleanup_expired_entries()

        return {
            'total_entries': self.stats.total_entries,
            'max_size': self.max_size,
            'utilization_percent': (self.stats.total_entries / self.max_size) * 100,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'hit_ratio': self.stats.get_hit_ratio_percent(),
            'evictions': self.stats.evictions,
            'invalidations': self.stats.invalidations,
            'strategy': self.strategy.value,
        }

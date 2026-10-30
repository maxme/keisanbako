"""Network status tracking and indicators for offline mode.

This module tracks network connectivity and provides indicators for the UI
to show when results are cached vs. live.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached value with metadata."""
    value: str
    timestamp: datetime
    source: str = "api"  # "api", "offline", "fallback"
    ttl_seconds: int = 3600  # Time to live

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    @property
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds."""
        return int((datetime.now() - self.timestamp).total_seconds())

    def format_age(self) -> str:
        """Format age in human-readable format."""
        age = self.age_seconds
        if age < 60:
            return f"{age}s ago"
        elif age < 3600:
            return f"{age // 60}m ago"
        else:
            return f"{age // 3600}h ago"


class NetworkStatus:
    """Track network connectivity status and cache information."""

    # Network status states
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"  # Some APIs working, some not

    def __init__(self):
        """Initialize network status tracker."""
        self._status = self.ONLINE
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._last_check = time.time()
        self._hit_count = 0
        self._miss_count = 0
        self._api_failures: Dict[str, int] = {}  # API name -> failure count

    @property
    def status(self) -> str:
        """Get current network status."""
        with self._lock:
            return self._status

    @property
    def is_online(self) -> bool:
        """Check if network is online."""
        return self.status == self.ONLINE

    @property
    def is_offline(self) -> bool:
        """Check if network is offline."""
        return self.status == self.OFFLINE

    def set_status(self, status: str) -> None:
        """Set network status."""
        if status not in [self.ONLINE, self.OFFLINE, self.DEGRADED]:
            raise ValueError(f"Invalid status: {status}")
        with self._lock:
            self._status = status

    def record_api_failure(self, api_name: str) -> None:
        """Record an API failure."""
        with self._lock:
            self._api_failures[api_name] = self._api_failures.get(api_name, 0) + 1

    def record_api_success(self, api_name: str) -> None:
        """Record an API success."""
        with self._lock:
            self._api_failures[api_name] = 0

    def get_api_status(self, api_name: str) -> str:
        """Get status for a specific API."""
        with self._lock:
            failures = self._api_failures.get(api_name, 0)
            if failures == 0:
                return "online"
            elif failures < 3:
                return "degraded"
            else:
                return "offline"

    def cache_set(self, key: str, value: str, source: str = "api", ttl_seconds: int = 3600) -> None:
        """Store a value in cache."""
        with self._lock:
            self._cache[key] = CacheEntry(value, datetime.now(), source, ttl_seconds)

    def cache_get(self, key: str) -> Optional[str]:
        """Get value from cache (returns None if expired or not found)."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if not entry.is_expired:
                    self._hit_count += 1
                    return entry.value
                else:
                    self._miss_count += 1
                    return None
            else:
                self._miss_count += 1
                return None

    def cache_get_with_metadata(self, key: str) -> Optional[tuple]:
        """Get value from cache with metadata (value, age_seconds, is_expired)."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if not entry.is_expired:
                    self._hit_count += 1
                else:
                    self._miss_count += 1
                return (entry.value, entry.age_seconds, entry.is_expired, entry.format_age())
            return None

    def cache_clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def cache_remove(self, key: str) -> None:
        """Remove a specific cache entry."""
        with self._lock:
            self._cache.pop(key, None)

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = (self._hit_count / total * 100) if total > 0 else 0
            return {
                "hits": self._hit_count,
                "misses": self._miss_count,
                "total": total,
                "hit_rate": f"{hit_rate:.1f}%",
                "cached_entries": len(self._cache),
                "api_failures": dict(self._api_failures),
            }

    def get_status_indicator(self) -> tuple:
        """Get status indicator for UI display.

        Returns:
            (status_color, status_text, tooltip)
        """
        status = self.status
        if status == self.ONLINE:
            return ("#4CAF50", "●", "Network: Online")
        elif status == self.DEGRADED:
            return ("#FFC107", "●", "Network: Degraded (some APIs offline)")
        else:
            return ("#F44336", "●", "Network: Offline (using cache)")


# Global network status instance
_network_status = NetworkStatus()


def get_network_status() -> NetworkStatus:
    """Get the global network status instance."""
    return _network_status

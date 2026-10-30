"""Test network status tracking and indicators.

Tests for cache management, network status tracking, and offline indicators.
"""

import unittest
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.network_status import NetworkStatus, CacheEntry, get_network_status


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry class."""

    def test_cache_entry_fresh(self):
        """Test that fresh cache entry is not expired."""
        entry = CacheEntry("value", datetime.now(), ttl_seconds=3600)
        self.assertFalse(entry.is_expired)

    def test_cache_entry_expired(self):
        """Test that old cache entry is expired."""
        old_time = datetime.now() - timedelta(hours=2)
        entry = CacheEntry("value", old_time, ttl_seconds=3600)
        self.assertTrue(entry.is_expired)

    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        entry = CacheEntry("value", datetime.now(), ttl_seconds=3600)
        age = entry.age_seconds
        self.assertLessEqual(age, 2)  # Should be very recent

    def test_cache_entry_format_age(self):
        """Test cache entry age formatting."""
        entry = CacheEntry("value", datetime.now() - timedelta(seconds=30), ttl_seconds=3600)
        formatted = entry.format_age()
        self.assertIn("s ago", formatted)


class TestNetworkStatus(unittest.TestCase):
    """Test NetworkStatus class."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_initial_status_online(self):
        """Test that initial status is online."""
        self.assertEqual(self.status.status, NetworkStatus.ONLINE)
        self.assertTrue(self.status.is_online)
        self.assertFalse(self.status.is_offline)

    def test_set_status_online(self):
        """Test setting status to online."""
        self.status.set_status(NetworkStatus.ONLINE)
        self.assertTrue(self.status.is_online)

    def test_set_status_offline(self):
        """Test setting status to offline."""
        self.status.set_status(NetworkStatus.OFFLINE)
        self.assertTrue(self.status.is_offline)
        self.assertFalse(self.status.is_online)

    def test_set_status_degraded(self):
        """Test setting status to degraded."""
        self.status.set_status(NetworkStatus.DEGRADED)
        self.assertEqual(self.status.status, NetworkStatus.DEGRADED)

    def test_invalid_status(self):
        """Test that invalid status raises error."""
        with self.assertRaises(ValueError):
            self.status.set_status("invalid")


class TestCacheOperations(unittest.TestCase):
    """Test cache operations."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_cache_set_get(self):
        """Test setting and getting cache values."""
        self.status.cache_set("key1", "value1")
        result = self.status.cache_get("key1")
        self.assertEqual(result, "value1")

    def test_cache_miss(self):
        """Test cache miss returns None."""
        result = self.status.cache_get("nonexistent")
        self.assertIsNone(result)

    def test_cache_expired(self):
        """Test that expired cache returns None."""
        # Set with very short TTL
        old_time = datetime.now() - timedelta(seconds=1)
        entry = CacheEntry("value", old_time, ttl_seconds=0)
        self.status._cache["key"] = entry

        result = self.status.cache_get("key")
        self.assertIsNone(result)

    def test_cache_clear(self):
        """Test clearing cache."""
        self.status.cache_set("key1", "value1")
        self.status.cache_set("key2", "value2")
        self.status.cache_clear()

        self.assertIsNone(self.status.cache_get("key1"))
        self.assertIsNone(self.status.cache_get("key2"))

    def test_cache_remove(self):
        """Test removing specific cache entry."""
        self.status.cache_set("key1", "value1")
        self.status.cache_set("key2", "value2")
        self.status.cache_remove("key1")

        self.assertIsNone(self.status.cache_get("key1"))
        self.assertEqual(self.status.cache_get("key2"), "value2")

    def test_cache_get_with_metadata(self):
        """Test getting cache with metadata."""
        self.status.cache_set("key", "value", ttl_seconds=3600)
        result = self.status.cache_get_with_metadata("key")

        self.assertIsNotNone(result)
        value, age, is_expired, formatted_age = result
        self.assertEqual(value, "value")
        self.assertFalse(is_expired)
        self.assertLessEqual(age, 2)
        self.assertIn("ago", formatted_age)


class TestAPIFailureTracking(unittest.TestCase):
    """Test API failure tracking."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_record_api_failure(self):
        """Test recording API failures."""
        self.status.record_api_failure("currency_api")
        self.status.record_api_failure("currency_api")
        self.assertEqual(self.status._api_failures["currency_api"], 2)

    def test_record_api_success(self):
        """Test recording API success resets count."""
        self.status.record_api_failure("currency_api")
        self.status.record_api_failure("currency_api")
        self.status.record_api_success("currency_api")
        self.assertEqual(self.status._api_failures["currency_api"], 0)

    def test_get_api_status_online(self):
        """Test API status when no failures."""
        self.status.record_api_success("currency_api")
        status = self.status.get_api_status("currency_api")
        self.assertEqual(status, "online")

    def test_get_api_status_degraded(self):
        """Test API status when degraded."""
        self.status.record_api_failure("currency_api")
        self.status.record_api_failure("currency_api")
        status = self.status.get_api_status("currency_api")
        self.assertEqual(status, "degraded")

    def test_get_api_status_offline(self):
        """Test API status when offline."""
        for _ in range(3):
            self.status.record_api_failure("currency_api")
        status = self.status.get_api_status("currency_api")
        self.assertEqual(status, "offline")


class TestCacheStats(unittest.TestCase):
    """Test cache statistics."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_cache_stats_empty(self):
        """Test cache stats when empty."""
        stats = self.status.get_cache_stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)
        self.assertEqual(stats["cached_entries"], 0)

    def test_cache_stats_with_hits(self):
        """Test cache stats with hits."""
        self.status.cache_set("key", "value")
        self.status.cache_get("key")
        self.status.cache_get("key")

        stats = self.status.get_cache_stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["cached_entries"], 1)

    def test_cache_stats_with_misses(self):
        """Test cache stats with misses."""
        self.status.cache_get("missing")
        self.status.cache_get("missing")

        stats = self.status.get_cache_stats()
        self.assertEqual(stats["misses"], 2)

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        self.status.cache_set("key", "value")
        self.status.cache_get("key")  # Hit
        self.status.cache_get("key")  # Hit
        self.status.cache_get("missing")  # Miss

        stats = self.status.get_cache_stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], "66.7%")


class TestStatusIndicator(unittest.TestCase):
    """Test status indicator for UI."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_online_indicator(self):
        """Test online status indicator."""
        self.status.set_status(NetworkStatus.ONLINE)
        color, text, tooltip = self.status.get_status_indicator()
        self.assertEqual(color, "#4CAF50")  # Green
        self.assertEqual(text, "●")
        self.assertIn("Online", tooltip)

    def test_offline_indicator(self):
        """Test offline status indicator."""
        self.status.set_status(NetworkStatus.OFFLINE)
        color, text, tooltip = self.status.get_status_indicator()
        self.assertEqual(color, "#F44336")  # Red
        self.assertEqual(text, "●")
        self.assertIn("Offline", tooltip)

    def test_degraded_indicator(self):
        """Test degraded status indicator."""
        self.status.set_status(NetworkStatus.DEGRADED)
        color, text, tooltip = self.status.get_status_indicator()
        self.assertEqual(color, "#FFC107")  # Yellow
        self.assertEqual(text, "●")
        self.assertIn("Degraded", tooltip)


class TestGlobalNetworkStatus(unittest.TestCase):
    """Test global network status instance."""

    def test_get_network_status_singleton(self):
        """Test that get_network_status returns same instance."""
        status1 = get_network_status()
        status2 = get_network_status()
        self.assertIs(status1, status2)

    def test_global_instance_operations(self):
        """Test operations on global instance."""
        status = get_network_status()
        status.cache_set("test_key", "test_value")
        result = status.cache_get("test_key")
        self.assertEqual(result, "test_value")


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of NetworkStatus."""

    def setUp(self):
        """Set up test instance."""
        self.status = NetworkStatus()

    def test_concurrent_cache_operations(self):
        """Test that cache operations are thread-safe."""
        import threading

        def set_values(key_prefix, count):
            for i in range(count):
                key = f"{key_prefix}_{i}"
                self.status.cache_set(key, f"value_{i}")

        def get_values(key_prefix, count):
            for i in range(count):
                key = f"{key_prefix}_{i}"
                self.status.cache_get(key)

        # Create threads
        threads = [
            threading.Thread(target=set_values, args=("thread1", 10)),
            threading.Thread(target=set_values, args=("thread2", 10)),
            threading.Thread(target=get_values, args=("thread1", 10)),
            threading.Thread(target=get_values, args=("thread2", 10)),
        ]

        # Run threads
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all values are stored
        self.assertEqual(len(self.status._cache), 20)


if __name__ == "__main__":
    unittest.main()

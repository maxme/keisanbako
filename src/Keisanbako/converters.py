"""Currency and unit conversion engines.

This module handles:
- Currency conversion via Frankfurter API and CoinGecko
- Unit conversion (length, weight, area, temperature)
- Caching and offline fallback
"""

import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from typing import Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlencode
import urllib.request

logger = logging.getLogger(__name__)

# Configuration
CURRENCY_MAP = {
    "yen": "JPY",
    "yens": "JPY",
    "jpy": "JPY",
    "euro": "EUR",
    "euros": "EUR",
    "eur": "EUR",
    "dollar": "USD",
    "dollars": "USD",
    "usd": "USD",
    "livre": "GBP",
    "livres": "GBP",
    "gbp": "GBP",
    "franc": "CHF",
    "francs": "CHF",
    "chf": "CHF",
    "aud": "AUD",
    "cad": "CAD",
    "btc": "BTC",
    "bitcoin": "BTC",
    "eth": "ETH",
    "ethereum": "ETH",
    "ada": "ADA",
    "cardano": "ADA",
    "sol": "SOL",
    "solana": "SOL",
    "doge": "DOGE",
    "dogecoin": "DOGE",
    "usdt": "USDT",
    "tether": "USDT",
}

CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "ADA": "cardano",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "USDT": "tether",
}

CURRENCY_API_URL = "https://api.frankfurter.app/latest"
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
API_TIMEOUT = 2
API_MAX_RETRIES = 2
CRYPTO_CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 hours for crypto
API_RETRY_DELAY = 1  # Start with 1 second delay between retries


class CurrencyConverter:
    """Handles currency conversion via Frankfurter API."""

    # Cache file for offline rates
    CACHE_FILE: Path = Path.home() / ".keisanbako_currency_cache.json"
    CACHE_TTL_SECONDS: int = 60 * 60  # 1 hour

    # In-memory request cache to deduplicate API calls
    _request_cache: Optional["RequestCache"] = None

    @classmethod
    def set_request_cache(cls, cache: "RequestCache") -> None:
        """Set the request cache for API call deduplication."""
        cls._request_cache = cache

    @staticmethod
    def _normalize_currency_code(currency_str: str) -> str:
        """Convert currency name or code to standard ISO 4217 code."""
        normalized = currency_str.strip().lower()
        return CURRENCY_MAP.get(normalized, currency_str.upper())

    @staticmethod
    def _get_crypto_cache_key(from_code: str, to_code: str) -> str:
        """Generate a cache key for crypto conversion pair."""
        return f"crypto:{from_code}:{to_code}"

    @staticmethod
    def _lookup_crypto_rate(from_code: str, to_code: str) -> Optional[float]:
        """Fetch a conversion rate from CoinGecko for crypto-to-fiat or crypto-to-crypto pairs."""
        from_id = CRYPTO_ID_MAP.get(from_code)
        to_id = CRYPTO_ID_MAP.get(to_code)
        if from_id is None and to_id is None:
            return None

        cache_key = CurrencyConverter._get_crypto_cache_key(from_code, to_code)

        # Check in-memory request cache first (5 second TTL for live requests)
        if CurrencyConverter._request_cache:
            cached_rate = CurrencyConverter._request_cache.get(cache_key)
            if cached_rate is not None:
                return cached_rate

        # Check persistent cache next
        try:
            if CurrencyConverter.CACHE_FILE.exists():
                with open(CurrencyConverter.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    crypto_cache = cache.get("crypto", {})
                    item = crypto_cache.get(cache_key)
                    if item:
                        if time.time() - item.get("timestamp", 0) < CRYPTO_CACHE_TTL_SECONDS:
                            cached_rate = item.get("rate")
                            if cached_rate is not None:
                                return float(cached_rate)
        except Exception:
            pass

        ids = []
        if from_id:
            ids.append(from_id)
        if to_id and to_id not in ids:
            ids.append(to_id)

        currency_keys = []
        for code in (from_code, to_code):
            key = code.lower()
            if key not in currency_keys:
                currency_keys.append(key)

        params = {
            "ids": ",".join(ids),
            "vs_currencies": ",".join(currency_keys),
        }
        url = f"{CRYPTO_API_URL}?{urlencode(params)}"

        # Retry with exponential backoff for rate limiting
        for attempt in range(API_MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                    data = json.loads(response.read().decode())

                    rate = None
                    if from_id and to_id:
                        rate = float(data.get(from_id, {}).get(to_id.lower(), 0.0))
                    elif from_id:
                        to_key = to_code.lower()
                        rate = float(data.get(from_id, {}).get(to_key, 0.0))
                    elif to_id:
                        from_key = from_code.lower()
                        rate = float(data.get(to_id, {}).get(from_key, 0.0))

                    if rate is not None and rate != 0.0:
                        # Cache in-memory for duplicate request deduplication
                        if CurrencyConverter._request_cache:
                            CurrencyConverter._request_cache.set(cache_key, rate)

                        # Cache the successful result to disk
                        try:
                            cache = {}
                            if CurrencyConverter.CACHE_FILE.exists():
                                with open(CurrencyConverter.CACHE_FILE, "r", encoding="utf-8") as f:
                                    cache = json.load(f)
                            crypto_cache = cache.get("crypto", {})
                            crypto_cache[cache_key] = {"rate": rate, "timestamp": time.time()}
                            cache["crypto"] = crypto_cache
                            with open(CurrencyConverter.CACHE_FILE, "w", encoding="utf-8") as f:
                                json.dump(cache, f)
                        except Exception:
                            pass
                        return rate
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Too Many Requests
                    delay = API_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"API rate limit (429). Attempt {attempt + 1}/{API_MAX_RETRIES}. Waiting {delay}s before retry.")
                    if attempt < API_MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        logger.warning(f"Crypto rate lookup failed after {API_MAX_RETRIES} attempts due to rate limiting")
                else:
                    logger.warning(f"Crypto API error {e.code}: {e.reason}")
                    break
            except urllib.error.URLError as e:
                logger.warning(f"Network error during crypto lookup: {e}")
                break
            except Exception as exc:
                logger.warning(f"Crypto rate lookup failed: {exc}")
                break

        return None

    @staticmethod
    def convert(amount: float, from_currency: str, to_currency: str) -> Optional[Tuple[float, str]]:
        """Convert amount from one currency to another."""
        from_code = CurrencyConverter._normalize_currency_code(from_currency)
        to_code = CurrencyConverter._normalize_currency_code(to_currency)

        is_crypto_from = from_code in CRYPTO_ID_MAP
        is_crypto_to = to_code in CRYPTO_ID_MAP
        if is_crypto_from or is_crypto_to:
            rate = CurrencyConverter._lookup_crypto_rate(from_code, to_code)
            if rate is None:
                return None
            if is_crypto_from and not is_crypto_to:
                return float(amount) * rate, to_code
            if not is_crypto_from and is_crypto_to:
                return float(amount) / rate, to_code
            return float(amount) * rate, to_code

        params = {
            "amount": amount,
            "from": from_code,
            "to": to_code,
        }

        url = f"{CURRENCY_API_URL}?{urlencode(params)}"

        try:
            if CurrencyConverter.CACHE_FILE.exists():
                with open(CurrencyConverter.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    key = f"{from_code}:{to_code}"
                    item = cache.get("pairs", {}).get(key)
                    if item:
                        if time.time() - item.get("timestamp", 0) < CurrencyConverter.CACHE_TTL_SECONDS:
                            per_unit = item.get("rate")
                            try:
                                converted = float(per_unit) * float(amount)
                                return converted, to_code
                            except Exception:
                                pass
        except Exception:
            pass

        for attempt in range(API_MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                    data = json.loads(response.read().decode())
                    rate = data["rates"][to_code]

                    try:
                        cache = {}
                        if CurrencyConverter.CACHE_FILE.exists():
                            with open(CurrencyConverter.CACHE_FILE, "r", encoding="utf-8") as f:
                                cache = json.load(f)
                        pairs = cache.get("pairs", {})
                        try:
                            per_unit_rate = float(rate) / float(amount) if float(amount) != 0 else 0.0
                        except Exception:
                            per_unit_rate = float(rate)
                        pairs[f"{from_code}:{to_code}"] = {"rate": per_unit_rate, "timestamp": time.time()}
                        cache["pairs"] = pairs
                        with open(CurrencyConverter.CACHE_FILE, "w", encoding="utf-8") as f:
                            json.dump(cache, f)
                    except Exception:
                        pass

                    return rate, to_code
            except URLError as e:
                logger.warning(f"Attempt {attempt + 1}/{API_MAX_RETRIES} failed: {e}")
                if attempt == API_MAX_RETRIES - 1:
                    logger.error(f"Currency conversion failed after {API_MAX_RETRIES} attempts")
                    try:
                        if CurrencyConverter.CACHE_FILE.exists():
                            with open(CurrencyConverter.CACHE_FILE, "r", encoding="utf-8") as f:
                                cache = json.load(f)
                                key = f"{from_code}:{to_code}"
                                item = cache.get("pairs", {}).get(key)
                                if item:
                                    per_unit = item.get("rate")
                                    try:
                                        converted = float(per_unit) * float(amount)
                                        return converted, to_code
                                    except Exception:
                                        return item.get("rate"), to_code
                    except Exception:
                        pass
                    return None
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Invalid API response: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error during currency conversion: {e}")
                return None

        return None


class UnitConverter:
    """Simple unit conversion for length, weight, area and temperature."""

    LENGTH_FACTORS = {
        "m": 1.0,
        "cm": 0.01,
        "mm": 0.001,
        "km": 1000.0,
        "in": 0.0254,
        "inch": 0.0254,
        "ft": 0.3048,
        "yd": 0.9144,
        "mi": 1609.344,
    }

    WEIGHT_FACTORS = {
        "kg": 1.0,
        "g": 0.001,
        "mg": 1e-6,
        "lb": 0.45359237,
        "oz": 0.0283495231,
    }

    AREA_FACTORS = {
        "m2": 1.0,
        "m²": 1.0,
        "cm2": 0.0001,
        "cm²": 0.0001,
        "km2": 1_000_000.0,
        "km²": 1_000_000.0,
        "mm2": 0.000001,
        "mm²": 0.000001,
        "ha": 10_000.0,
        "hectare": 10_000.0,
        "acre": 4046.8564,
        "acres": 4046.8564,
        "sq ft": 0.092903,
        "sqft": 0.092903,
        "sq in": 0.00064516,
        "sqin": 0.00064516,
        "in2": 0.00064516,
        "in²": 0.00064516,
        "ft2": 0.092903,
        "ft²": 0.092903,
    }

    SPEED_FACTORS = {
        "m/s": 1.0,
        "km/h": 1.0 / 3.6,
        "mph": 0.44704,
        "mi/h": 0.44704,
        "knots": 0.51444,
        "ft/s": 0.3048,
    }

    @staticmethod
    def convert(amount: float, from_unit: str, to_unit: str) -> Optional[Tuple[float, str]]:
        """Convert amount from one unit to another.

        Args:
            amount: The quantity to convert.
            from_unit: Source unit.
            to_unit: Target unit.

        Returns:
            Tuple of (converted_amount, to_unit) or None if conversion not supported.
        """
        f = from_unit.lower()
        t = to_unit.lower()

        # Length conversions
        if f in UnitConverter.LENGTH_FACTORS and t in UnitConverter.LENGTH_FACTORS:
            meters = amount * UnitConverter.LENGTH_FACTORS[f]
            converted = meters / UnitConverter.LENGTH_FACTORS[t]
            return converted, to_unit

        # Weight conversions
        if f in UnitConverter.WEIGHT_FACTORS and t in UnitConverter.WEIGHT_FACTORS:
            kgs = amount * UnitConverter.WEIGHT_FACTORS[f]
            converted = kgs / UnitConverter.WEIGHT_FACTORS[t]
            return converted, to_unit

        # Area conversions
        if f in UnitConverter.AREA_FACTORS and t in UnitConverter.AREA_FACTORS:
            square_meters = amount * UnitConverter.AREA_FACTORS[f]
            converted = square_meters / UnitConverter.AREA_FACTORS[t]
            return converted, to_unit

        # Speed/velocity conversions
        if f in UnitConverter.SPEED_FACTORS and t in UnitConverter.SPEED_FACTORS:
            meters_per_sec = amount * UnitConverter.SPEED_FACTORS[f]
            converted = meters_per_sec / UnitConverter.SPEED_FACTORS[t]
            return converted, to_unit

        # Temperature conversions (special-case)
        if f in ("c", "celsius") and t in ("f", "fahrenheit"):
            return (amount * 9.0 / 5.0) + 32.0, to_unit
        if f in ("f", "fahrenheit") and t in ("c", "celsius"):
            return (amount - 32.0) * 5.0 / 9.0, to_unit
        if f in ("c", "celsius") and t in ("k", "kelvin"):
            return amount + 273.15, to_unit
        if f in ("k", "kelvin") and t in ("c", "celsius"):
            return amount - 273.15, to_unit

        return None


class RequestCache:
    """Simple in-memory cache for API requests to avoid duplicates."""

    def __init__(self, ttl_seconds: float = 5.0) -> None:
        """Initialize request cache.

        Args:
            ttl_seconds: Time-to-live for cached requests.
        """
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, Tuple[float, Optional[float]]] = {}

    def get_key(self, operation: str, from_val: str, to_val: str) -> str:
        """Generate a cache key."""
        return f"{operation}:{from_val}:{to_val}".lower()

    def get(self, key: str) -> Optional[float]:
        """Get cached value if not expired."""
        if key in self.cache:
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Optional[float]) -> None:
        """Cache a value."""
        self.cache[key] = (time.time(), value)

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()

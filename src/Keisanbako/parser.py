"""Input parsing and expression preprocessing for calculator.

This module handles:
- Parsing input expressions (currency, units, scientific notation, timedeltas)
- Normalizing various input formats
- Detecting and normalizing currency symbols
- Processing timedelta notation into Python timedelta() calls
"""

import re
from datetime import timedelta
from typing import Optional, Tuple


# ============================================================================
# Expression Parsing
# ============================================================================


class ExpressionParser:
    """Handles parsing and preprocessing of calculator expressions."""

    # Currency pattern: "amount currency in/to target_currency"
    CURRENCY_PATTERN = re.compile(
        r"^([\d\.]+)\s*([a-zA-Z]+)\s+(?:in|to)\s+([a-zA-Z]+)$", re.IGNORECASE
    )

    # Timedelta patterns
    TIMEDELTA_PATTERNS = [
        (r"(\d+)\s*days?", r"timedelta(days=\1)"),
        (r"(\d+)\s*weeks?", r"timedelta(weeks=\1)"),
        (r"(\d+)\s*months?", r"timedelta(days=\1*30)"),  # Approximate
        (r"(\d+)\s*years?", r"timedelta(days=\1*365)"),  # Approximate
        (r"(\d+)\s*hours?", r"timedelta(hours=\1)"),
        (r"(\d+)\s*mins?", r"timedelta(minutes=\1)"),
        (r"(\d+)\s*minutes?", r"timedelta(minutes=\1)"),
        (r"(\d+)\s*secs?", r"timedelta(seconds=\1)"),
        (r"(\d+)\s*seconds?", r"timedelta(seconds=\1)"),
    ]

    # Scientific notation pattern (e.g., 1e5, 2.5e-3, 1E+10)
    SCIENTIFIC_NOTATION_PATTERN = re.compile(
        r"(\d+\.?\d*)\s*[eE]\s*([+-]?\s*\d+)",
        re.IGNORECASE,
    )

    # Assignment pattern: let x = 5  OR x = 5 OR x := 5
    ASSIGN_PATTERN = re.compile(r"^\s*(?:let\s+)?([a-zA-Z_]\w*)\s*(?:=|:=)\s*(.+)$")

    # Function definition pattern: f(x) = x * 2  OR let f(a,b) := a+b
    FUNCTION_DEF_PATTERN = re.compile(
        r"^\s*(?:let\s+)?([a-zA-Z_]\w*)\s*\(\s*([a-zA-Z_,\s]*)\s*\)\s*(?:=|:=)\s*(.+)$"
    )

    # Unit pattern: same shape as currency pattern (allow digits for units like m2, cm2)
    # Also support composite units like m/s, km/h, ft/s, etc.
    UNIT_PATTERN = re.compile(
        r"^([\d\.]+)\s*([a-zA-Z0-9²³²/]+)\s+(?:in|to)\s+([a-zA-Z0-9²³²/]+)$", re.IGNORECASE
    )

    # Map of currency symbols to their codes
    CURRENCY_SYMBOLS = {
        "€": "EUR",
        "$": "USD",
        "£": "GBP",
        "¥": "JPY",
        "円": "JPY",  # Japanese yen character
        "₹": "INR",
        "₽": "RUB",
        "₩": "KRW",
        "₪": "ILS",
        "₦": "NGN",
        "₨": "PKR",
        "₱": "PHP",
        "₡": "CRC",
        "₲": "PYG",
        "₴": "UAH",
        "₵": "GHS",
    }

    @staticmethod
    def is_comment(expression: str) -> bool:
        """Check if expression is a comment.

        Args:
            expression: The expression string.

        Returns:
            True if expression starts with '#'.
        """
        return expression.strip().startswith("#")

    @staticmethod
    def is_incomplete_currency(expression: str, currency_map: dict, unit_factors: dict) -> bool:
        """Return True while the user is still typing a currency target name.

        Args:
            expression: The expression string.
            currency_map: Mapping of currency names/codes.
            unit_factors: Combined unit factors for validation.

        Returns:
            True if expression appears incomplete.
        """
        expr = expression.strip()
        if not expr:
            return False

        match = re.fullmatch(r"([\d\.]+)\s*([A-Za-z]+)\s+(?:in|to)\s*([A-Za-z]*)", expr, re.IGNORECASE)
        if not match:
            return False

        _, _, target = match.groups()
        if not target:
            return True

        target_lower = target.lower()

        # Unit conversions are complete valid inputs and should never be blocked
        unit_targets = set(unit_factors.keys()) | {"c", "celsius", "f", "fahrenheit", "k", "kelvin"}
        if target_lower in unit_targets:
            return False

        recognized = {token.lower() for token in currency_map} | {value.lower() for value in currency_map.values()}
        if target_lower in recognized:
            return False
        return any(token.startswith(target_lower) for token in recognized)

    @staticmethod
    def normalize_scientific_notation(expression: str) -> str:
        """Normalize scientific notation to Python format.

        Converts patterns like "1e5", "2.5e-3", "1 e 5" to valid Python format.

        Args:
            expression: Expression with scientific notation.

        Returns:
            Expression with normalized scientific notation.
        """
        def normalize_match(match):
            mantissa, exponent = match.groups()
            # Remove spaces from exponent (e.g., "- 3" becomes "-3")
            exponent_clean = exponent.replace(" ", "")
            return f"{mantissa}e{exponent_clean}"

        normalized = ExpressionParser.SCIENTIFIC_NOTATION_PATTERN.sub(
            normalize_match, expression
        )
        return normalized

    @staticmethod
    def process_timedeltas(expression: str) -> str:
        """Replace timedelta notation with Python timedelta() calls.

        Args:
            expression: Expression with timedelta notation.

        Returns:
            Expression with timedeltas replaced.
        """
        processed = expression

        # Convert "today" to "today()" if not already followed by "("
        processed = re.sub(r"today(?!\()", "today()", processed)

        # Normalize arithmetic expressions immediately after a + or - before a time unit
        value_pattern = (
            r"(?:\((?:[^()]|\([^()]*\))*\)|\d+(?:\.\d+)?)"
            r"(?:\s*[+\-*/]\s*(?:\((?:[^()]|\([^()]*\))*\)|\d+(?:\.\d+)?))*"
        )
        unit_pattern = r"days?|weeks?|months?|years?|hours?|minutes?|seconds?"
        processed = re.sub(
            rf"(?P<prefix>[+\-])\s*(?P<delta>{value_pattern})\s*(?P<unit>{unit_pattern})",
            lambda m: (
                f"{m.group('prefix')} timedelta({m.group('unit').lower()}={m.group('delta')})"
                if m.group('unit').lower() in {"days", "weeks", "hours", "minutes", "seconds"}
                else f"{m.group('prefix')} timedelta(days={m.group('delta')})"
            ),
            processed,
            flags=re.IGNORECASE,
        )

        # Handle cases where a parenthesized expression is followed directly by a time unit
        processed = re.sub(r"\)\s*days?", r") * timedelta(days=1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*weeks?", r") * timedelta(weeks=1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*months?", r") * timedelta(days=30)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*years?", r") * timedelta(days=365)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*hours?", r") * timedelta(hours=1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*minutes?", r") * timedelta(minutes=1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"\)\s*seconds?", r") * timedelta(seconds=1)", processed, flags=re.IGNORECASE)

        # Support parenthesized expressions before time units
        processed = re.sub(r"(\([^\)]+\))\s*days?", r"timedelta(days=\1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*weeks?", r"timedelta(weeks=\1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*months?", r"timedelta(days=\1*30)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*years?", r"timedelta(days=\1*365)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*hours?", r"timedelta(hours=\1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*minutes?", r"timedelta(minutes=\1)", processed, flags=re.IGNORECASE)
        processed = re.sub(r"(\([^\)]+\))\s*seconds?", r"timedelta(seconds=\1)", processed, flags=re.IGNORECASE)

        for pattern, replacement in ExpressionParser.TIMEDELTA_PATTERNS:
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
        
        # Fix missing operators between adjacent timedeltas or between timedelta and bare numbers
        # E.g., "timedelta(...) timedelta(...)" -> "timedelta(...) + timedelta(...)"
        # E.g., "timedelta(...) 30" -> "timedelta(...) + 30"
        # E.g., "timedelta(...)timedelta(...)" -> "timedelta(...) + timedelta(...)" (when spaces removed)
        processed = re.sub(
            r"(timedelta\([^)]+\))(?:\s*)(?=timedelta\(|\d+(?:\s*[a-zA-Z])?)",
            r"\1 + ",
            processed
        )
        
        return processed

    @staticmethod
    def detect_and_normalize_currency_symbols(expression: str) -> Tuple[str, Optional[str]]:
        """Detect currency symbols in expression and return cleaned expression.

        Args:
            expression: Expression that may contain currency symbols.

        Returns:
            Tuple of (cleaned_expression, currency_code or None)
        """
        # Check which currency symbols are present
        found_symbols = [sym for sym in ExpressionParser.CURRENCY_SYMBOLS if sym in expression]

        # If no currency symbols, return as is
        if not found_symbols:
            return expression, None

        # If multiple different symbols, it's ambiguous - return error signal
        if len(found_symbols) > 1:
            return expression, None

        symbol = found_symbols[0]
        currency_code = ExpressionParser.CURRENCY_SYMBOLS[symbol]

        # Remove the symbol from the expression
        cleaned = expression.replace(symbol, "").strip()

        # Verify the cleaned expression is still valid for evaluation
        if re.search(r"\d", cleaned):
            return cleaned, currency_code

        return expression, None

"""Expression evaluation engine for the calculator.

This module handles safe evaluation of mathematical expressions, including:
- Basic arithmetic and math functions
- Currency conversion
- Unit conversion
- Date arithmetic
- User-defined variables and functions
"""

import logging
import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Tuple, Callable, Any, Dict

from .parser import ExpressionParser

logger = logging.getLogger(__name__)


def _date_safe(year_or_first: int, month_or_second: Optional[int] = None, day_or_third: Optional[int] = None) -> date:
    """Create a date with improved error handling and detection of wrong argument order.

    Args:
        year_or_first: First argument (should be year in Python order)
        month_or_second: Second argument (should be month)
        day_or_third: Third argument (should be day)

    Returns:
        datetime.date object

    Raises:
        ValueError: With helpful error message if arguments are in wrong order

    Examples:
        _date_safe(2026, 10, 22) -> date(2026, 10, 22)  # Correct order
        _date_safe(22, 10, 2026) -> ValueError with suggestion to use date_fr()
    """
    # Handle missing arguments
    if month_or_second is None or day_or_third is None:
        raise ValueError("date() requires 3 arguments: year, month, day")

    year = year_or_first
    month = month_or_second
    day = day_or_third

    # Validate that values are integers
    try:
        year = int(year)
        month = int(month)
        day = int(day)
    except (TypeError, ValueError):
        raise ValueError("date() arguments must be integers")

    # Detect if user provided French format (day, month, year) by mistake
    # French format would have: first arg 1-31, second arg 1-12, third arg > 1900
    is_likely_french_format = (
        1 <= year <= 31 and  # First arg looks like a day (1-31)
        1 <= month <= 12 and  # Second arg looks like a month (1-12)
        day > 1900  # Third arg looks like a year (> 1900)
    )

    if is_likely_french_format:
        raise ValueError(
            f"date() uses Python order: year, month, day.\n"
            f"You provided: {year}, {month}, {day}\n"
            f"Did you mean French format? Use date_fr({year}, {month}, {day}) instead."
        )

    # Try to create the date with Python order
    try:
        return date(year, month, day)
    except ValueError as e:
        raise ValueError(f"Invalid date: {str(e)}\nUse format: date(year, month, day) or date_fr(day, month, year)")


@dataclass
class CalculationResult:
    """Result of a calculation operation."""

    value: str
    is_error: bool = False
    currency: Optional[str] = None
    error_type: Optional[str] = None  # "syntax", "undefined", "zero_division", "unsupported", etc.
    is_cached: bool = False  # True if value comes from offline cache
    error_message: Optional[str] = None  # Full error message with hint
    raw_value: Optional[float] = None  # numeric value before formatting, used to set `ans`


class ExpressionEvaluator:
    """Safely evaluates mathematical and date expressions."""

    # Safe functions available to expressions
    SAFE_FUNCTIONS: Dict[str, Callable] = {
        **{k: v for k, v in math.__dict__.items() if not k.startswith("_")},
        "abs": abs,
        "round": round,
        "today": lambda: date.today(),
        "date": _date_safe,
        "timedelta": timedelta,
    }

    # User variables / macros (class-level dictionary shared across instances)
    USER_VARS: Dict[str, Any] = {}

    # Error messages with hints
    ERROR_HINTS: Dict[str, str] = {
        "syntax": "Check expression syntax. Use parentheses () for grouping.",
        "undefined": "Unknown function or variable. Try: +, -, *, /, **, sqrt, sin, cos, tan, etc.",
        "zero_division": "Cannot divide by zero. Check your expression.",
        "invalid": "Invalid expression. Examples: 1+2, sqrt(16), today+30 days",
    }

    @staticmethod
    def get_error_message(
        error_type: str,
        expression: str = "",
        exception: Optional[Exception] = None,
        translator_fn: Optional[Callable[[str], str]] = None,
    ) -> str:
        """Generate a user-friendly error message with hint based on error type.

        Args:
            error_type: Type of error (syntax, undefined, zero_division, unsupported, etc.)
            expression: The expression that caused the error
            exception: The exception that was raised (if any)
            translator_fn: Translation function (optional)

        Returns:
            User-friendly error message with helpful hint
        """
        # Use translator if provided, otherwise use English defaults
        translate = translator_fn or (lambda x: x)

        messages: Dict[str, str] = {
            "syntax": translate("error_syntax"),
            "undefined_var": translate("error_undefined_var"),
            "undefined_func": translate("error_undefined_func"),
            "zero_division": translate("error_zero_division"),
            "invalid_type": translate("error_invalid_type"),
            "unsupported_currency": translate("error_unsupported_currency"),
            "unsupported_unit": translate("error_unsupported_unit"),
            "invalid_amount": translate("error_invalid_amount"),
        }

        base_message = messages.get(error_type, translate("error_calculation"))

        # Add specific details if exception is provided
        if exception and isinstance(exception, NameError):
            # Try to extract variable name from error message
            match = re.search(r"name '(\w+)' is not defined", str(exception))
            if match:
                var_name = match.group(1)
                # Return localized message with the variable name
                undefined_msg = translate("error_undefined_var_name")
                return f"{undefined_msg}: '{var_name}'"

        if exception and isinstance(exception, ZeroDivisionError):
            return translate("error_zero_division")

        return base_message

    # Class-level default instance for backward compatibility with static method calls
    _default_instance: Optional["ExpressionEvaluator"] = None

    @classmethod
    def _get_default_instance(cls) -> "ExpressionEvaluator":
        """Get or create the default evaluator instance."""
        if cls._default_instance is None:
            from .settings import format_number, format_date
            from .converters import UnitConverter, CURRENCY_MAP, CurrencyConverter
            from .translations import t
            cls._default_instance = cls(
                format_number_fn=format_number,
                format_date_fn=format_date,
                currency_converter=CurrencyConverter,
                unit_converter=UnitConverter,
                translator_fn=t,
                currency_map=CURRENCY_MAP,
                unit_factors={**UnitConverter.LENGTH_FACTORS, **UnitConverter.WEIGHT_FACTORS, **UnitConverter.AREA_FACTORS}
            )
        return cls._default_instance

    def __init__(
        self,
        format_number_fn: Optional[Callable[[Any], str]] = None,
        format_date_fn: Optional[Callable[[date], str]] = None,
        currency_converter: Optional[Any] = None,
        unit_converter: Optional[Any] = None,
        translator_fn: Optional[Callable[[str], str]] = None,
        currency_map: Optional[Dict[str, str]] = None,
        unit_factors: Optional[Dict[str, float]] = None,
    ) -> None:
        """Initialize the evaluator with dependencies.

        Args:
            format_number_fn: Function to format numbers (default: str)
            format_date_fn: Function to format dates (default: isoformat)
            currency_converter: CurrencyConverter instance
            unit_converter: UnitConverter instance
            translator_fn: Translation function
            currency_map: Mapping of currency names to codes
            unit_factors: Combined unit conversion factors
        """
        self.format_number: Callable[[Any], str] = format_number_fn or (lambda x: str(x))
        self.format_date: Callable[[date], str] = format_date_fn or (lambda x: x.isoformat())
        self.currency_converter: Any = currency_converter
        self.unit_converter: Any = unit_converter
        self.translator: Callable[[str], str] = translator_fn or (lambda x: "Error")
        self.currency_map: Dict[str, str] = currency_map or {}
        self.unit_factors: Dict[str, float] = unit_factors or {}

    @staticmethod
    def _is_comment(expression: str) -> bool:
        """Check if expression is a comment."""
        return ExpressionParser.is_comment(expression)

    @staticmethod
    def _is_incomplete_currency(expression: str, currency_map: dict, unit_factors: dict) -> bool:
        """Return True while the user is still typing a currency target name."""
        return ExpressionParser.is_incomplete_currency(expression, currency_map, unit_factors)

    def _try_currency_conversion(self, expression: str) -> Optional[Tuple[str, Optional[float]]]:
        """Try to evaluate as currency conversion."""
        if not self.currency_converter:
            return None

        # First try standard pattern without symbols
        match = ExpressionParser.CURRENCY_PATTERN.match(expression)
        if match:
            amount_str, from_curr, to_curr = match.groups()
            try:
                amount = float(amount_str)
                result = self.currency_converter.convert(amount, from_curr, to_curr)
                if result:
                    rate, to_code = result
                    return f"{self.format_number(rate)} {to_code}", float(rate)
            except ValueError:
                logger.error(f"Invalid amount: {amount_str}")
            return "Error", None

        # Try with currency symbols
        symbol_chars = r"[€$£¥円₹₽₩₪₦₨₱₡₲₴₵]"
        symbol_pattern = rf"^({symbol_chars}?)\s*([\d\.]+)\s*({symbol_chars}?)\s*([a-zA-Z]+)?\s+(?:in|to)\s+([a-zA-Z]+)$"
        symbol_match = re.match(symbol_pattern, expression, re.IGNORECASE)

        if symbol_match:
            leading_symbol, amount_str, trailing_symbol, from_curr_name, to_curr = symbol_match.groups()

            # Determine source currency from symbol
            symbol = trailing_symbol or leading_symbol
            if symbol and symbol in ExpressionParser.CURRENCY_SYMBOLS:
                from_curr = ExpressionParser.CURRENCY_SYMBOLS[symbol]
            elif from_curr_name:
                from_curr = from_curr_name
            else:
                return None

            try:
                amount = float(amount_str)
                result = self.currency_converter.convert(amount, from_curr, to_curr)
                if result:
                    rate, to_code = result
                    return f"{self.format_number(rate)} {to_code}", float(rate)
            except ValueError:
                logger.error(f"Invalid amount: {amount_str}")
            return "Error", None

        # Try arithmetic expression with currency conversion
        expr_with_currency_pattern = rf"^(.+?)\s+([a-zA-Z]+)\s+(?:in|to)\s+([a-zA-Z]+)$"
        expr_match = re.match(expr_with_currency_pattern, expression, re.IGNORECASE)

        if expr_match:
            expr_part, from_curr, to_curr = expr_match.groups()

            try:
                # Evaluate the arithmetic expression part
                result_calc = self.evaluate(expr_part)

                if not result_calc.is_error:
                    result_str = result_calc.value.replace(" ", "").replace(",", ".")
                    result_str = re.sub(r"[^0-9.\-]", "", result_str)

                    if result_str and result_str != "-":
                        amount = float(result_str)
                        conversion_result = self.currency_converter.convert(amount, from_curr, to_curr)
                        if conversion_result:
                            rate, to_code = conversion_result
                            return f"{self.format_number(rate)} {to_code}", float(rate)
            except (ValueError, AttributeError) as e:
                logger.debug(f"Arithmetic currency conversion failed: {e}")

        return None

    def _try_duration_conversion(self, expression: str) -> Optional[str]:
        """Support time-duration conversions like '30 hours + 2 days in hours'."""
        match = re.fullmatch(
            r"(?P<lhs>.+?)\s+(?:in|to)\s+(?P<unit>days?|hours?|(?:minutes?|mins?)|(?:seconds?|secs?)|weeks?|months?|years?)\s*$",
            expression,
            re.IGNORECASE,
        )
        if not match:
            return None

        lhs, unit_name = match.groups()
        if not re.search(r"(?:days?|hours?|(?:minutes?|mins?)|(?:seconds?|secs?)|weeks?|months?|years?)", lhs, re.IGNORECASE):
            return None

        try:
            processed_lhs = ExpressionParser.process_timedeltas(lhs)
            ctx = {**self.SAFE_FUNCTIONS, **self.USER_VARS}
            total_delta = eval(processed_lhs, {"__builtins__": {}}, ctx)
            if not isinstance(total_delta, timedelta):
                return None

            target_unit = unit_name.lower()
            if target_unit in ("min", "mins"):
                target_unit = "minute"
            elif target_unit in ("sec", "secs"):
                target_unit = "second"
            else:
                target_unit = target_unit.rstrip("s")

            factors = {
                "week": 7 * 24 * 60 * 60,
                "day": 24 * 60 * 60,
                "hour": 60 * 60,
                "minute": 60,
                "second": 1,
                "month": 30 * 24 * 60 * 60,
                "year": 365 * 24 * 60 * 60,
            }
            if target_unit not in factors:
                return None

            value = total_delta.total_seconds() / factors[target_unit]
            formatted = self.format_number(value)
            return f"{formatted} {unit_name.lower()}"
        except Exception as exc:
            logger.debug(f"Duration conversion failed for '{expression}': {exc}")
            return "Error"

    def _try_unit_conversion(self, expression: str) -> Optional[Tuple[str, Optional[float]]]:
        """Try to evaluate as a unit conversion."""
        if not self.unit_converter:
            return None

        match = ExpressionParser.UNIT_PATTERN.match(expression)
        if not match:
            return None

        amount_str, from_unit, to_unit = match.groups()
        try:
            amount = float(amount_str)
        except ValueError:
            logger.error(f"Invalid amount: {amount_str}")
            return "Error", None

        # Only treat as unit conversion when units are recognized
        f = from_unit.lower()
        t = to_unit.lower()

        result = self.unit_converter.convert(amount, from_unit, to_unit)
        if result:
            converted, unit = result
            return f"{self.format_number(converted)} {unit}", float(converted)

        return None

    # Static wrapper for backward compatibility with tests
    def evaluate(expression_or_self: Any, expression: Optional[str] = None) -> CalculationResult:
        """Evaluate a mathematical, date, or currency expression.

        Can be called as:
        - ExpressionEvaluator.evaluate("1+1")  # static/class method (backward compat)
        - evaluator_instance.evaluate("1+1")   # instance method

        Args:
            expression_or_self: Either the expression string (static) or self (instance)
            expression: The expression string (only for static calls)

        Returns:
            CalculationResult with value and error flag.
        """
        # Determine if this is a static call or instance call
        if isinstance(expression_or_self, str) and expression is None:
            # Static call: ExpressionEvaluator.evaluate("expression")
            expr_str = expression_or_self
            evaluator = ExpressionEvaluator._get_default_instance()
            return evaluator._evaluate_impl(expr_str)
        elif isinstance(expression_or_self, ExpressionEvaluator):
            # Instance call: self.evaluate("expression")
            # expression_or_self is 'self', expression is the expr string
            return expression_or_self._evaluate_impl(expression)
        else:
            # Fallback for static calls on the class itself
            # This handles ExpressionEvaluator.evaluate("expression") calls
            expr_str = expression_or_self
            evaluator = ExpressionEvaluator._get_default_instance()
            return evaluator._evaluate_impl(expr_str)

    def _evaluate_impl(self, expression: str) -> CalculationResult:
        """Internal implementation of evaluate.

        Args:
            expression: The expression to evaluate.

        Returns:
            CalculationResult with value and error flag.
        """
        expression = expression.strip()

        # Handle empty or comment expressions
        if not expression or self._is_comment(expression):
            return CalculationResult("", is_error=False)

        # While the user is still typing the target currency, do not block the input
        if self._is_incomplete_currency(expression, self.currency_map, self.unit_factors):
            return CalculationResult("", is_error=False)

        # Handle function definitions first: f(x)=... or let f(a,b) := ...
        func_match = ExpressionParser.FUNCTION_DEF_PATTERN.match(expression)
        if func_match:
            func_name, args_str, rhs = func_match.groups()
            args = [a.strip() for a in args_str.split(",") if a.strip()]
            # Validate arg names
            for a in args:
                if not re.match(r"^[A-Za-z_]\w*$", a):
                    error_msg = self.get_error_message("syntax", expression, translator_fn=self.translator)
                    return CalculationResult("Error", is_error=True, error_type="syntax", error_message=error_msg)
            # Build lambda expression
            args_code = ",".join(args)
            lambda_code = f"lambda {args_code}: ({rhs})"
            try:
                ctx_locals = {**self.SAFE_FUNCTIONS, **self.USER_VARS}
                func = eval(lambda_code, {"__builtins__": {}}, ctx_locals)
                self.USER_VARS[func_name] = func
                return CalculationResult(func_name, is_error=False)
            except Exception as e:
                logger.debug(f"Function definition error for '{expression}': {e}")
                error_msg = self.get_error_message("syntax", expression, e, translator_fn=self.translator)
                return CalculationResult("Error", is_error=True, error_type="syntax", error_message=error_msg)

        # Handle assignments: let x = 5, x = 5, x := 5
        assign_match = ExpressionParser.ASSIGN_PATTERN.match(expression)
        if assign_match:
            var_name, rhs = assign_match.groups()
            clean_rhs = rhs.replace(" ", "")
            normalized_rhs = ExpressionParser.normalize_scientific_notation(clean_rhs)
            processed_rhs = ExpressionParser.process_timedeltas(normalized_rhs)
            try:
                ctx = {**self.SAFE_FUNCTIONS, **self.USER_VARS}
                val = eval(processed_rhs, {"__builtins__": {}}, ctx)
                self.USER_VARS[var_name] = val
                if isinstance(val, (int, float)):
                    return CalculationResult(self.format_number(val), is_error=False, raw_value=float(val))
                return CalculationResult(str(val), is_error=False)
            except NameError as e:
                logger.debug(f"Assignment error for '{expression}': {e}")
                error_msg = self.get_error_message("undefined_var", expression, e, translator_fn=self.translator)
                return CalculationResult("Error", is_error=True, error_type="undefined", error_message=error_msg)
            except Exception as e:
                logger.debug(f"Assignment error for '{expression}': {e}")
                error_msg = self.get_error_message("invalid_type", expression, e, translator_fn=self.translator)
                return CalculationResult("Error", is_error=True, error_type="invalid", error_message=error_msg)

        # Remove spaces for evaluation
        clean_expr = expression.replace(" ", "")

        # Try duration conversion before generic unit conversion
        duration_result = self._try_duration_conversion(expression)
        if duration_result is not None:
            is_error = duration_result == "Error"
            return CalculationResult(duration_result, is_error=is_error)

        # Try unit conversion first
        unit_result = self._try_unit_conversion(expression)
        if unit_result is not None:
            unit_str, unit_raw = unit_result
            is_error = unit_str == "Error"
            return CalculationResult(unit_str, is_error=is_error, raw_value=unit_raw)

        # Try currency conversion next
        currency_result = self._try_currency_conversion(expression)
        if currency_result is not None:
            curr_str, curr_raw = currency_result
            is_error = curr_str == "Error"
            return CalculationResult(curr_str, is_error=is_error, raw_value=curr_raw)

        # Detect and normalize currency symbols
        expr_with_currency, detected_currency = ExpressionParser.detect_and_normalize_currency_symbols(clean_expr)

        # Normalize scientific notation
        normalized_expr = ExpressionParser.normalize_scientific_notation(expr_with_currency)

        # Process timedelta notation
        processed_expr = ExpressionParser.process_timedeltas(normalized_expr)

        # Evaluate the expression
        try:
            ctx = {**self.SAFE_FUNCTIONS, **self.USER_VARS}
            result = eval(processed_expr, {"__builtins__": {}}, ctx)

            # Format the result
            if isinstance(result, (int, float)):
                formatted = self.format_number(result)
                # Add currency symbol if detected
                if detected_currency:
                    symbol_map = {
                        "EUR": "€",
                        "USD": "$",
                        "GBP": "£",
                        "JPY": "¥",
                        "INR": "₹",
                        "RUB": "₽",
                        "KRW": "₩",
                        "ILS": "₪",
                        "NGN": "₦",
                        "PKR": "₨",
                        "PHP": "₱",
                        "CRC": "₡",
                        "PYG": "₲",
                        "UAH": "₴",
                        "GHS": "₵",
                    }
                    symbol = symbol_map.get(detected_currency, detected_currency)
                    formatted = f"{formatted}{symbol}"
                return CalculationResult(formatted, is_error=False, currency=detected_currency, raw_value=float(result))
            elif isinstance(result, date):
                return CalculationResult(self.format_date(result), is_error=False)
            return CalculationResult(str(result), is_error=False)

        except SyntaxError as e:
            logger.debug(f"Syntax error in expression '{expression}': {e}")
            error_msg = self.get_error_message("syntax", expression, e, translator_fn=self.translator)
            return CalculationResult("Error", is_error=True, error_type="syntax", error_message=error_msg)
        except ZeroDivisionError as e:
            logger.debug(f"Zero division in expression '{expression}': {e}")
            error_msg = self.get_error_message("zero_division", expression, e, translator_fn=self.translator)
            return CalculationResult("Error", is_error=True, error_type="zero_division", error_message=error_msg)
        except NameError as e:
            logger.debug(f"Name error in expression '{expression}': {e}")
            error_msg = self.get_error_message("undefined_var", expression, e, translator_fn=self.translator)
            return CalculationResult("Error", is_error=True, error_type="undefined", error_message=error_msg)
        except ValueError as e:
            logger.debug(f"Value error in expression '{expression}': {e}")
            error_msg = self.get_error_message("invalid_type", expression, e, translator_fn=self.translator)
            return CalculationResult("Error", is_error=True, error_type="invalid", error_message=error_msg)
        except Exception as e:
            logger.error(f"Unexpected error evaluating '{expression}': {e}")
            error_msg = self.get_error_message("invalid", expression, e, translator_fn=self.translator)
            return CalculationResult("Error", is_error=True, error_type="invalid", error_message=error_msg)

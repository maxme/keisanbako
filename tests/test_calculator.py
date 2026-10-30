"""Tests for the Keisanbako calculator.

This module contains unit tests for the calculator logic, including:
- Number formatting
- Expression evaluation
- Currency conversion (mocked)
- Edge cases and error handling
- Performance testing
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import sys
from pathlib import Path
import tempfile

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.settings import format_number, format_date
from Keisanbako.converters import CurrencyConverter, UnitConverter, CURRENCY_MAP, RequestCache
from Keisanbako.evaluator import ExpressionEvaluator, CalculationResult
from Keisanbako.parser import ExpressionParser
from Keisanbako.ui import CalculatorWindow
from Keisanbako.translations import t
from PySide6.QtWidgets import QApplication
import json


class TestFormatNumber(unittest.TestCase):
    """Tests for number formatting with thousands separators."""

    def test_format_integer_no_separator(self):
        """Test formatting integer with no separator needed."""
        self.assertEqual(format_number(42), "42")

    def test_format_integer_with_separator(self):
        """Test formatting integer with thousands separator."""
        self.assertEqual(format_number(1000), "1 000")

    def test_format_large_integer(self):
        """Test formatting large integer."""
        self.assertEqual(format_number(1234567), "1 234 567")

    def test_format_float(self):
        """Test formatting float."""
        self.assertEqual(format_number(1234.56), "1 234.56")

    def test_format_float_whole_number(self):
        """Test formatting float that's a whole number."""
        self.assertEqual(format_number(1000.0), "1 000")

    def test_format_small_float(self):
        """Test formatting small float."""
        self.assertEqual(format_number(0.123), "0.123")

    def test_format_hides_float_noise(self):
        """Binary rounding noise is not shown to the user."""
        self.assertEqual(format_number(28.799999999999997), "28.8")
        self.assertEqual(format_number(32.186879999999995), "32.18688")
        self.assertEqual(format_number(0.1 + 0.2), "0.3")

    def test_format_noise_that_rounds_to_whole_number(self):
        """Noise that rounds to an integer is shown as an integer."""
        self.assertEqual(format_number(2.9999999999999996), "3")

    def test_format_repeating_decimal_is_truncated(self):
        """Repeating decimals are capped at the display precision."""
        self.assertEqual(format_number(1 / 3), "0.3333333333")

    def test_format_negative_number(self):
        """Test formatting negative number."""
        self.assertEqual(format_number(-1000), "-1 000")

    def test_format_zero(self):
        """Test formatting zero."""
        self.assertEqual(format_number(0), "0")

    def test_format_non_numeric(self):
        """Test formatting non-numeric value."""
        self.assertEqual(format_number("abc"), "abc")

    def test_format_number_respects_thousands_separator_setting(self):
        """Formatting should follow the active configuration when a separator is chosen."""
        from Keisanbako.settings import SettingsManager

        original = SettingsManager.get().copy()
        try:
            SettingsManager.get().update({"thousands_separator": ",", "decimal_separator": "."})
            self.assertEqual(format_number(1234567.89), "1,234,567.89")
            SettingsManager.get().update({"thousands_separator": " "})
            self.assertEqual(format_number(1234567.89), "1 234 567.89")
        finally:
            SettingsManager.get().update(original)


class TestCurrencyConverter(unittest.TestCase):
    """Tests for currency conversion."""

    def setUp(self):
        """Use a temporary cache file to isolate tests from user cache."""
        self._orig_cache = CurrencyConverter.CACHE_FILE
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()
        CurrencyConverter.CACHE_FILE = Path(tmp.name)

    def tearDown(self):
        """Restore original cache file and remove temp file."""
        try:
            if CurrencyConverter.CACHE_FILE.exists():
                CurrencyConverter.CACHE_FILE.unlink()
        finally:
            CurrencyConverter.CACHE_FILE = self._orig_cache

    def test_normalize_currency_code_lowercase_name(self):
        """Test normalizing lowercase currency name."""
        result = CurrencyConverter._normalize_currency_code("yen")
        self.assertEqual(result, "JPY")

    def test_normalize_currency_code_uppercase_code(self):
        """Test normalizing uppercase currency code."""
        result = CurrencyConverter._normalize_currency_code("USD")
        self.assertEqual(result, "USD")

    def test_normalize_currency_code_unknown(self):
        """Test normalizing unknown currency code."""
        result = CurrencyConverter._normalize_currency_code("XYZ")
        self.assertEqual(result, "XYZ")

    def test_normalize_currency_plural(self):
        """Test normalizing plural currency name."""
        result = CurrencyConverter._normalize_currency_code("dollars")
        self.assertEqual(result, "USD")

    @patch("Keisanbako.converters.urllib.request.urlopen")
    def test_convert_success(self, mock_urlopen):
        """Test successful currency conversion."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"rates": {"EUR": 0.92}}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = CurrencyConverter.convert(100, "USD", "EUR")

        self.assertIsNotNone(result)
        amount, code = result
        self.assertAlmostEqual(amount, 0.92)
        self.assertEqual(code, "EUR")

    @patch("Keisanbako.converters.urllib.request.urlopen")
    def test_convert_with_currency_names(self, mock_urlopen):
        """Test conversion with currency names."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"rates": {"EUR": 0.92}}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = CurrencyConverter.convert(100, "dollar", "euro")

        self.assertIsNotNone(result)
        amount, code = result
        self.assertEqual(code, "EUR")

    @patch("Keisanbako.converters.urllib.request.urlopen")
    def test_convert_crypto_to_fiat(self, mock_urlopen):
        """Test conversion from BTC to EUR using a crypto market rate."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"bitcoin": {"eur": 50000.0}}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = CurrencyConverter.convert(1, "BTC", "EUR")

        self.assertIsNotNone(result)
        amount, code = result
        self.assertAlmostEqual(amount, 50000.0)
        self.assertEqual(code, "EUR")

    @patch("Keisanbako.converters.urllib.request.urlopen")
    def test_convert_api_failure(self, mock_urlopen):
        """Test conversion when API fails."""
        mock_urlopen.side_effect = Exception("Network error")

        result = CurrencyConverter.convert(100, "USD", "EUR")

        self.assertIsNone(result)

    @patch("Keisanbako.converters.urllib.request.urlopen")
    def test_convert_invalid_response(self, mock_urlopen):
        """Test conversion with invalid API response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid json"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = CurrencyConverter.convert(100, "USD", "EUR")

        self.assertIsNone(result)


class TestExpressionEvaluator(unittest.TestCase):
    """Tests for expression evaluation."""

    def setUp(self):
        """Set up test evaluator."""
        from Keisanbako.converters import UnitConverter
        from Keisanbako.settings import format_number, format_date
        self.evaluator = ExpressionEvaluator(
            format_number_fn=format_number,
            format_date_fn=format_date,
            currency_converter=CurrencyConverter,
            unit_converter=UnitConverter,
            translator_fn=t,
            currency_map=CURRENCY_MAP,
            unit_factors={**UnitConverter.LENGTH_FACTORS, **UnitConverter.WEIGHT_FACTORS, **UnitConverter.AREA_FACTORS}
        )

    def test_is_comment(self):
        """Test comment detection."""
        self.assertTrue(ExpressionEvaluator._is_comment("# This is a comment"))
        self.assertFalse(ExpressionEvaluator._is_comment("42"))

    # ========== Basic Arithmetic ==========

    def test_evaluate_simple_addition(self):
        """Test simple addition."""
        result = self.evaluator.evaluate("2+3")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "5")

    def test_evaluate_complex_arithmetic(self):
        """Test complex arithmetic expression."""
        result = self.evaluator.evaluate("10 * 5 + 2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "52")

    def test_evaluate_division(self):
        """Test division."""
        result = self.evaluator.evaluate("10 / 2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "5")

    def test_evaluate_power(self):
        """Test power operation."""
        result = self.evaluator.evaluate("2 ** 10")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "1 024")

    # ========== Math Functions ==========

    def test_evaluate_abs(self):
        """Test absolute value function."""
        result = self.evaluator.evaluate("abs(-5)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "5")

    def test_evaluate_round(self):
        """Test round function."""
        result = self.evaluator.evaluate("round(3.7)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "4")

    def test_evaluate_sqrt(self):
        """Test square root."""
        result = self.evaluator.evaluate("sqrt(16)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "4")

    def test_evaluate_sin(self):
        """Test sine function."""
        result = self.evaluator.evaluate("sin(0)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "0")

    # ========== Date Arithmetic ==========

    def test_evaluate_timedelta_days(self):
        """Test timedelta with days."""
        result = self.evaluator.evaluate("today() + 30 days")
        self.assertFalse(result.is_error)
        # Result should be a date 30 days from today
        self.assertIn("20", result.value)  # Should contain a year

    def test_evaluate_timedelta_days_no_parentheses(self):
        """Test timedelta with days without parentheses on today."""
        result = self.evaluator.evaluate("today + 30 days")
        self.assertFalse(result.is_error)
        # Result should be a date 30 days from today
        self.assertIn("20", result.value)  # Should contain a year

    def test_evaluate_timedelta_weeks(self):
        """Test timedelta with weeks."""
        result = self.evaluator.evaluate("today() + 2 weeks")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_weeks_no_parentheses(self):
        """Test timedelta with weeks without parentheses on today."""
        result = self.evaluator.evaluate("today + 2 weeks")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_months(self):
        """Test timedelta with months."""
        result = self.evaluator.evaluate("today() + 3 months")
        self.assertFalse(result.is_error)

    def test_complex_expression_timedelta(self):
        """Ensure nested arithmetic inside timedelta is handled."""
        result = self.evaluator.evaluate("today + ((1280 - 400) / 20) days")
        self.assertFalse(result.is_error)
        self.assertIn("20", result.value)

    def test_equivalent_timedelta_forms_produce_same_result(self):
        """Both parenthesized arithmetic styles should be accepted as equivalent."""
        left = self.evaluator.evaluate("today + ((1280 - 400) / 20) days")
        right = self.evaluator.evaluate("today + (1280 - 400) / 20 days")

        self.assertFalse(left.is_error)
        self.assertFalse(right.is_error)
        self.assertEqual(left.value, right.value)

    def test_evaluate_timedelta_months_no_parentheses(self):
        """Test timedelta with months without parentheses on today."""
        result = self.evaluator.evaluate("today + 3 months")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_years(self):
        """Test timedelta with years."""
        result = self.evaluator.evaluate("today() + 1 years")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_years_no_parentheses(self):
        """Test timedelta with years without parentheses on today."""
        result = self.evaluator.evaluate("today + 1 years")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_subtraction(self):
        """Test timedelta subtraction."""
        result = self.evaluator.evaluate("today() - 5 days")
        self.assertFalse(result.is_error)

    def test_evaluate_timedelta_subtraction_no_parentheses(self):
        """Test timedelta subtraction without parentheses on today."""
        result = self.evaluator.evaluate("today - 5 days")
        self.assertFalse(result.is_error)

    def test_evaluate_date_comparison(self):
        """Test date comparison."""
        result = self.evaluator.evaluate("today() >= date(2020, 1, 1)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "True")

    def test_evaluate_multiple_time_units_with_minutes_and_seconds(self):
        """Test addition of multiple time units: 24 mins + 7 mins 30 secs."""
        result = self.evaluator.evaluate("24 mins + 7 mins 30 secs")
        self.assertFalse(result.is_error)
        # Result should be 31 minutes 30 seconds
        self.assertEqual(result.value, "0:31:30")

    def test_evaluate_multiple_time_units_compact_format(self):
        """Test addition of time units without full spacing: 24 mins + 7mins 30 secs."""
        result = self.evaluator.evaluate("24 mins + 7mins 30 secs")
        self.assertFalse(result.is_error)
        # Result should be 31 minutes 30 seconds
        self.assertEqual(result.value, "0:31:30")

    def test_evaluate_consecutive_time_units_no_spaces(self):
        """Test consecutive time units with minimal spacing."""
        result = self.evaluator.evaluate("10 mins + 5 secs")
        self.assertFalse(result.is_error)
        # Result should be 10 minutes 5 seconds
        self.assertEqual(result.value, "0:10:05")

    # ========== Currency Conversion ==========

    @patch("Keisanbako.converters.CurrencyConverter.convert")
    def test_evaluate_currency_conversion(self, mock_convert):
        """Test currency conversion evaluation."""
        mock_convert.return_value = (92.0, "EUR")

        result = self.evaluator.evaluate("100 USD in EUR")

        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "92 EUR")

    @patch("Keisanbako.converters.CurrencyConverter.convert")
    def test_evaluate_currency_conversion_failure(self, mock_convert):
        """Test currency conversion failure."""
        mock_convert.return_value = None

        result = self.evaluator.evaluate("100 USD in EUR")

        self.assertTrue(result.is_error)
        self.assertEqual(result.value, t("error_message"))

    def test_evaluate_incomplete_currency_does_not_block_input(self):
        """Typing a partial target currency should leave the input unblocked; a complete one should convert."""
        for value in ["100 eur in y", "100 eur in ye"]:
            with self.subTest(value=value):
                result = self.evaluator.evaluate(value)
                self.assertFalse(result.is_error)
                self.assertEqual(result.value, "")

        result = self.evaluator.evaluate("100 eur in yen")
        self.assertFalse(result.is_error)
        self.assertNotEqual(result.value, "")

    # ========== Empty and Comment ==========

    def test_evaluate_empty_string(self):
        """Test empty string evaluation."""
        result = self.evaluator.evaluate("")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "")

    def test_evaluate_comment(self):
        """Test comment evaluation."""
        result = self.evaluator.evaluate("# This is a comment")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "")

    # ========== Error Handling ==========

    def test_evaluate_syntax_error(self):
        """Test syntax error handling."""
        result = self.evaluator.evaluate("2 ++")
        self.assertTrue(result.is_error)
        self.assertEqual(result.value, t("error_message"))

    def test_evaluate_division_by_zero(self):
        """Test division by zero."""
        result = self.evaluator.evaluate("1 / 0")
        self.assertTrue(result.is_error)

    def test_evaluate_undefined_variable(self):
        """Test undefined variable error."""
        result = self.evaluator.evaluate("undefined_var")
        self.assertTrue(result.is_error)

    def test_evaluate_undefined_function(self):
        """Test undefined function error."""
        result = self.evaluator.evaluate("undefined_func()")
        self.assertTrue(result.is_error)

    def test_evaluate_mixed_time_units_are_valid(self):
        """These duration expressions should parse and not be rejected."""
        for value in ["1 mins + 40 hours", "1 min + 40 hours", "22 hour in days"]:
            with self.subTest(value=value):
                result = self.evaluator.evaluate(value)
                self.assertFalse(result.is_error)

    def test_evaluate_mixed_duration_with_conversion_is_valid(self):
        """An explicit duration sum converted to a target unit should work."""
        result = self.evaluator.evaluate("30 hours + 2 days in hours")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "78 hours")

    def test_evaluate_import_blocked(self):
        """Test that imports are blocked."""
        result = self.evaluator.evaluate("__import__('os').system('ls')")
        self.assertTrue(result.is_error)

    # ========== Formatting ==========

    def test_evaluate_large_number_formatting(self):
        """Test that large numbers are formatted with separators."""
        result = self.evaluator.evaluate("1000000 + 234567")
        self.assertFalse(result.is_error)
        self.assertIn(" ", result.value)  # Should contain spaces

    # ========== Complex Expressions ==========

    def test_evaluate_mixed_expression(self):
        """Test mixed arithmetic expression."""
        result = self.evaluator.evaluate("abs(-10) * 2 + sqrt(16)")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "24")

    def test_evaluate_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        result1 = self.evaluator.evaluate("2 + 3")
        result2 = self.evaluator.evaluate("2+3")
        self.assertEqual(result1.value, result2.value)


class TestCalculationResult(unittest.TestCase):
    """Tests for CalculationResult dataclass."""

    def test_result_success(self):
        """Test successful result."""
        result = CalculationResult("42", is_error=False)
        self.assertEqual(result.value, "42")
        self.assertFalse(result.is_error)

    def test_result_error(self):
        """Test error result."""
        result = CalculationResult(t("error_message"), is_error=True)
        self.assertEqual(result.value, t("error_message"))
        self.assertTrue(result.is_error)


class TestTimedeltaProcessing(unittest.TestCase):
    """Tests for timedelta pattern processing."""

    def test_process_timedeltas_days(self):
        """Test processing 'days' pattern."""
        result = ExpressionParser.process_timedeltas("5 days")
        self.assertIn("timedelta", result)

    def test_process_timedeltas_weeks(self):
        """Test processing 'weeks' pattern."""
        result = ExpressionParser.process_timedeltas("2 weeks")
        self.assertIn("timedelta", result)

    def test_process_timedeltas_today_without_parentheses(self):
        """Test that 'today' is converted to 'today()'."""
        result = ExpressionParser.process_timedeltas("today + 30 days")
        self.assertIn("today()", result)

    def test_process_timedeltas_today_with_parentheses_unchanged(self):
        """Test that 'today()' with parentheses is not changed."""
        result = ExpressionParser.process_timedeltas("today() + 30 days")
        self.assertIn("today()", result)
        # Should not have double parentheses
        self.assertNotIn("today()()", result)

    def test_process_timedeltas_multiple_patterns(self):
        """Test processing multiple timedelta patterns."""
        result = ExpressionParser.process_timedeltas("today + 5 days + 2 weeks")
        self.assertIn("today()", result)
        self.assertIn("timedelta(days=5)", result)
        self.assertIn("timedelta(weeks=2)", result)


class TestScientificNotation(unittest.TestCase):
    """Tests for scientific notation support."""

    def setUp(self):
        """Set up test evaluator."""
        self.evaluator = ExpressionEvaluator()

    def test_scientific_notation_basic(self):
        """Test basic scientific notation."""
        result = self.evaluator.evaluate("1e5")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "100 000")

    def test_scientific_notation_decimal(self):
        """Test scientific notation with decimal mantissa."""
        result = self.evaluator.evaluate("2.5e3")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "2 500")

    def test_scientific_notation_negative_exponent(self):
        """Test scientific notation with negative exponent."""
        result = self.evaluator.evaluate("1e-2")
        self.assertFalse(result.is_error)
        # Should be 0.01
        self.assertIn("0.01", result.value)

    def test_scientific_notation_positive_exponent(self):
        """Test scientific notation with explicit positive exponent."""
        result = self.evaluator.evaluate("5e+2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "500")

    def test_scientific_notation_lowercase_e(self):
        """Test scientific notation with lowercase 'e'."""
        result = self.evaluator.evaluate("3e4")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "30 000")

    def test_scientific_notation_uppercase_e(self):
        """Test scientific notation with uppercase 'E'."""
        result = self.evaluator.evaluate("3E4")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "30 000")

    def test_scientific_notation_with_spaces(self):
        """Test scientific notation with spaces around 'e'."""
        result = self.evaluator.evaluate("1 e 5")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "100 000")

    def test_scientific_notation_with_spaces_around_exponent_sign(self):
        """Test scientific notation with spaces around exponent sign."""
        result = self.evaluator.evaluate("2.5 e - 3")
        self.assertFalse(result.is_error)
        # Should be 0.0025
        self.assertIn("0.0025", result.value)

    def test_scientific_notation_in_arithmetic(self):
        """Test scientific notation in arithmetic expression."""
        result = self.evaluator.evaluate("1e3 + 1e3")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "2 000")

    def test_scientific_notation_multiplication(self):
        """Test scientific notation in multiplication."""
        result = self.evaluator.evaluate("1e2 * 2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "200")

    def test_scientific_notation_normalize_method(self):
        """Test _normalize_scientific_notation method."""
        result = ExpressionParser.normalize_scientific_notation("1 e 5")
        self.assertEqual(result, "1e5")

    def test_scientific_notation_normalize_with_spaces(self):
        """Test _normalize_scientific_notation with various spacing."""
        result = ExpressionParser.normalize_scientific_notation("2.5 E - 3")
        self.assertEqual(result.lower(), "2.5e-3")

    def test_scientific_notation_very_large(self):
        """Test very large scientific notation."""
        result = self.evaluator.evaluate("1e10")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "10 000 000 000")

    def test_scientific_notation_very_small(self):
        """Test very small scientific notation."""
        result = self.evaluator.evaluate("1e-10")
        self.assertFalse(result.is_error)
        # Result should be a very small decimal number
        # Check that it's formatted and doesn't error
        self.assertTrue(len(result.value) > 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for calculator."""

    def setUp(self):
        """Set up test evaluator."""
        self.evaluator = ExpressionEvaluator()

    def test_simple_expression_performance(self):
        """Test that simple expressions evaluate quickly."""
        start = time.time()
        for _ in range(1000):
            result = self.evaluator.evaluate("2 + 3")
        elapsed = time.time() - start

        # Should evaluate 1000 simple expressions in less than 1 second
        self.assertLess(elapsed, 1.0)
        self.assertFalse(result.is_error)

    def test_complex_expression_performance(self):
        """Test that complex expressions evaluate in reasonable time."""
        start = time.time()
        result = self.evaluator.evaluate("sqrt(16) * abs(-10) + pow(2, 8) - sin(0) + cos(0)")
        elapsed = time.time() - start

        # Complex expression should evaluate in less than 100ms
        self.assertLess(elapsed, 0.1)
        self.assertFalse(result.is_error)

    def test_large_number_performance(self):
        """Test performance with very large numbers."""
        start = time.time()
        result = self.evaluator.evaluate("1e308 / 2")
        elapsed = time.time() - start

        # Should handle large numbers quickly
        self.assertLess(elapsed, 0.1)
        self.assertFalse(result.is_error)

    def test_deeply_nested_expression_performance(self):
        """Test performance with deeply nested expressions."""
        # Create a deeply nested expression: ((((1+1)+1)+1)+1)+...
        expr = "1"
        for _ in range(50):
            expr = f"({expr} + 1)"

        start = time.time()
        result = self.evaluator.evaluate(expr)
        elapsed = time.time() - start

        # Should evaluate nested expressions in less than 100ms
        self.assertLess(elapsed, 0.1)
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "51")

    def test_multiple_evaluations_performance(self):
        """Test performance of multiple sequential evaluations."""
        expressions = [
            "100 + 200",
            "sqrt(144)",
            "2 ** 10",
            "sin(0) + cos(0)",
            "abs(-42)",
            "round(3.7)",
            "10 * 5 + 2",
            "100 / 5",
        ]

        start = time.time()
        for _ in range(100):
            for expr in expressions:
                self.evaluator.evaluate(expr)
        elapsed = time.time() - start

        # 800 evaluations should complete in less than 1 second
        self.assertLess(elapsed, 1.0)

    def test_date_arithmetic_performance(self):
        """Test performance of date arithmetic."""
        start = time.time()
        for _ in range(100):
            self.evaluator.evaluate("today + 30 days")
        elapsed = time.time() - start

        # 100 date calculations should complete in less than 1 second
        self.assertLess(elapsed, 1.0)

    def test_formatting_performance(self):
        """Test performance of number formatting."""
        start = time.time()
        for _ in range(1000):
            format_number(1234567890)
        elapsed = time.time() - start

        # 1000 format operations should complete in less than 0.5 seconds
        self.assertLess(elapsed, 0.5)

    def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        start = time.time()
        for _ in range(1000):
            self.evaluator.evaluate("invalid ++ expression")
        elapsed = time.time() - start

        # Error handling should be just as fast as normal evaluation
        self.assertLess(elapsed, 1.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete calculator workflows."""

    def setUp(self):
        """Set up test evaluator."""
        self.evaluator = ExpressionEvaluator()

    def test_workflow_simple_calculation(self):
        """Test simple calculation workflow."""
        result = self.evaluator.evaluate("100 * 2 + 50")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "250")

    def test_workflow_multiple_operations(self):
        """Test multiple operations in sequence."""
        results = [
            self.evaluator.evaluate("10 + 20"),
            self.evaluator.evaluate("30 * 2"),
            self.evaluator.evaluate("60 - 10"),
        ]

        for result in results:
            self.assertFalse(result.is_error)

        self.assertEqual(results[0].value, "30")
        self.assertEqual(results[1].value, "60")
        self.assertEqual(results[2].value, "50")

    @patch("Keisanbako.converters.CurrencyConverter.convert")
    def test_workflow_mixed_operations(self, mock_convert):
        """Test workflow with mixed operation types."""
        # Arithmetic
        result1 = self.evaluator.evaluate("1000 + 500")
        self.assertFalse(result1.is_error)

        # Currency
        mock_convert.return_value = (1000.0, "EUR")
        result2 = self.evaluator.evaluate("1000 USD in EUR")
        self.assertFalse(result2.is_error)

        # Date
        result3 = self.evaluator.evaluate("today() + 1 days")
        self.assertFalse(result3.is_error)


class TestUnitConversion(unittest.TestCase):
    """Tests for unit conversion support."""

    def setUp(self):
        self.evaluator = ExpressionEvaluator()

    def test_length_conversion_cm_to_m(self):
        result = self.evaluator.evaluate("100 cm in m")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "1 m")

    def test_weight_conversion_kg_to_g(self):
        result = self.evaluator.evaluate("2 kg in g")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "2 000 g")

    def test_temperature_conversion_f_to_c(self):
        result = self.evaluator.evaluate("32 F in C")
        self.assertFalse(result.is_error)
        self.assertTrue(result.value.startswith("0"))

    def test_area_conversion_m2_to_ha(self):
        """Test area conversion from square meters to hectares."""
        result = self.evaluator.evaluate("100m2 in ha")
        self.assertFalse(result.is_error)
        self.assertIn("0.01", result.value)
        self.assertIn("ha", result.value)

    def test_area_conversion_ha_to_m2(self):
        """Test area conversion from hectares to square meters."""
        result = self.evaluator.evaluate("1 ha in m2")
        self.assertFalse(result.is_error)
        self.assertIn("10 000", result.value)
        self.assertIn("m2", result.value)

    def test_area_conversion_km2_to_ha(self):
        """Test area conversion from square kilometers to hectares."""
        result = self.evaluator.evaluate("100 km2 in ha")
        self.assertFalse(result.is_error)
        self.assertIn("10 000", result.value)
        self.assertIn("ha", result.value)

    def test_area_conversion_acre_to_m2(self):
        """Test area conversion from acres to square meters."""
        result = self.evaluator.evaluate("1 acre in m2")
        self.assertFalse(result.is_error)
        self.assertIn("4 046", result.value)
        self.assertIn("m2", result.value)

    def test_area_conversion_cm2_to_m2(self):
        """Test area conversion from square centimeters to square meters."""
        result = self.evaluator.evaluate("1000 cm2 in m2")
        self.assertFalse(result.is_error)
        self.assertIn("0.1", result.value)
        self.assertIn("m2", result.value)

    def test_speed_conversion_ms_to_kmh(self):
        """Test speed conversion from m/s to km/h."""
        result = self.evaluator.evaluate("8 m/s in km/h")
        self.assertFalse(result.is_error)
        # 8 m/s = 28.8 km/h
        self.assertIn("28", result.value)
        self.assertIn("km/h", result.value)

    def test_speed_conversion_kmh_to_ms(self):
        """Test speed conversion from km/h to m/s."""
        result = self.evaluator.evaluate("100 km/h in m/s")
        self.assertFalse(result.is_error)
        # 100 km/h = 27.777... m/s
        self.assertIn("27", result.value)
        self.assertIn("m/s", result.value)

    def test_speed_conversion_mph_to_kmh(self):
        """Test speed conversion from mph to km/h."""
        result = self.evaluator.evaluate("50 mph in km/h")
        self.assertFalse(result.is_error)
        # 50 mph ≈ 80.47 km/h
        self.assertIn("80", result.value)
        self.assertIn("km/h", result.value)

    def test_speed_conversion_knots_to_ms(self):
        """Test speed conversion from knots to m/s."""
        result = self.evaluator.evaluate("30 knots in m/s")
        self.assertFalse(result.is_error)
        # 30 knots ≈ 15.43 m/s
        self.assertIn("15", result.value)
        self.assertIn("m/s", result.value)

    def test_speed_conversion_fts_to_ms(self):
        """Test speed conversion from ft/s to m/s."""
        result = self.evaluator.evaluate("1 ft/s in m/s")
        self.assertFalse(result.is_error)
        # 1 ft/s = 0.3048 m/s
        self.assertIn("0.3048", result.value)
        self.assertIn("m/s", result.value)


class TestVariablesAndExport(unittest.TestCase):
    """Tests for variable assignment and export functionality."""

    def test_variable_assignment_and_usage(self):
        evaluator = ExpressionEvaluator()
        res = evaluator.evaluate("x = 5")
        self.assertFalse(res.is_error)
        self.assertEqual(res.value, "5")

        res2 = evaluator.evaluate("x + 2")
        self.assertFalse(res2.is_error)
        self.assertEqual(res2.value, "7")

    def test_export_history_to_path(self):
        # Create a minimal QApplication for widgets
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()
        # Populate history via the internal entries list
        win._history_entries = ["1+1 = 2", "100 cm in m = 1 m"]

        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()

        success = win.export_history_to_path(tmp.name, fmt="json")
        self.assertTrue(success)
        # Verify file content
        with open(tmp.name, "r") as f:
            data = json.load(f)
            self.assertIn("entries", data)
            self.assertTrue(len(data["entries"]) >= 1)


class TestFunctions(unittest.TestCase):
    """Tests for user-defined functions/macro support."""

    def test_function_definition_and_call(self):
        evaluator = ExpressionEvaluator()
        # Define function
        res = evaluator.evaluate("f(x) = x * 2")
        self.assertFalse(res.is_error)
        self.assertIn("f", ExpressionEvaluator.USER_VARS)

        # Call function
        res2 = evaluator.evaluate("f(5)")
        self.assertFalse(res2.is_error)
        self.assertEqual(res2.value, "10")

    def test_function_multiple_args(self):
        evaluator = ExpressionEvaluator()
        res = evaluator.evaluate("add(a, b) = a + b")
        self.assertFalse(res.is_error)
        res2 = evaluator.evaluate("add(3, 4)")
        self.assertFalse(res2.is_error)
        self.assertEqual(res2.value, "7")


class TestCurrencyCache(unittest.TestCase):
    """Tests for currency conversion cache behavior."""

    def test_cached_conversion_used(self):
        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()

        # Prepare cache
        cache = {"pairs": {"USD:EUR": {"rate": 0.92, "timestamp": time.time()}}}
        with open(tmp.name, "w") as f:
            json.dump(cache, f)

        # Point CurrencyConverter to this cache
        old = CurrencyConverter.CACHE_FILE
        CurrencyConverter.CACHE_FILE = Path(tmp.name)
        try:
            res = CurrencyConverter.convert(100, "USD", "EUR")
            self.assertIsNotNone(res)
            amount, code = res
            # Cache stores a per-unit rate; conversion should scale by the requested amount
            self.assertAlmostEqual(amount, 0.92 * 100)
            self.assertEqual(code, "EUR")
        finally:
            CurrencyConverter.CACHE_FILE = old


class TestMenuActions(unittest.TestCase):
    """Tests for menu bar actions (Export and Help)."""

    def test_export_history_via_menu(self):
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()
        win.history_browser.setPlainText("1+1 = 2\n100 cm in m = 1 m\n")

        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()

        with (
            patch(
                "Keisanbako.ui.QFileDialog.getSaveFileName",
                return_value=(tmp.name, "JSON Files (*.json)"),
            ) as mock_save,
            patch("Keisanbako.ui.QMessageBox.information") as mock_info,
        ):
            # Locate File -> Export History action
            menubar = win.menuBar()
            file_action = next((a for a in menubar.actions() if a.text() == t("menu_file")), None)
            self.assertIsNotNone(file_action)
            file_menu = file_action.menu()
            export_action = next(
                (a for a in file_menu.actions() if a.text() == t("action_export_history")), None
            )
            self.assertIsNotNone(export_action)

            # Trigger export
            export_action.trigger()

            mock_save.assert_called()
            mock_info.assert_called()

            # Verify file written
            with open(tmp.name, "r") as f:
                data = json.load(f)
                self.assertIn("entries", data)

    def test_help_menu_shows_dialog(self):
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()

        with patch("Keisanbako.ui.QMessageBox.information") as mock_info:
            menubar = win.menuBar()
            help_action = next((a for a in menubar.actions() if a.text() == t("menu_help")), None)
            self.assertIsNotNone(help_action)
            help_menu = help_action.menu()
            show_action = next((a for a in help_menu.actions() if a.text() == t("action_help")), None)
            self.assertIsNotNone(show_action)

            show_action.trigger()
            mock_info.assert_called()


class TestHistoryClear(unittest.TestCase):
    """Tests for clearing history via the handler/button."""

    def test_clear_history_handler(self):
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()

        import tempfile

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()

        # Point history file to temp to avoid touching user's real file
        win.HISTORY_FILE = Path(tmp.name)

        # Populate history
        win._history_entries = ["1+1 = 2", "100 cm in m = 1 m"]
        win._render_history()

        # Call handler without confirmation (tests skip dialogs)
        win._clear_history(confirm=False)

        self.assertEqual(win._history_entries, [])
        self.assertEqual(win._history_list, [])

        # Verify persisted history is empty
        with open(tmp.name, "r") as f:
            data = json.load(f)
        self.assertEqual(data.get("entries", []), [])

        try:
            Path(tmp.name).unlink()
        except Exception:
            pass


class TestInputHistory(unittest.TestCase):
    """Tests for input box history navigation using Up/Down arrows."""

    def test_input_history_navigation(self):
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()

        # Seed history list (simulate loaded history)
        win._history_entries = ["1+1 = 2", "2+2 = 4", "3+3 = 6"]

        # Start with empty input
        win.input_field.setText("")

        # Up should go to last entry
        win._history_prev()
        self.assertEqual(win.input_field.text(), "3+3")

        # Further up navigates backward
        win._history_prev()
        self.assertEqual(win.input_field.text(), "2+2")

        win._history_prev()
        self.assertEqual(win.input_field.text(), "1+1")

        # Down should navigate forward
        win._history_next()
        self.assertEqual(win.input_field.text(), "2+2")

        win._history_next()
        self.assertEqual(win.input_field.text(), "3+3")

        # Past the last entry restores original (empty) buffer
        win._history_next()
        self.assertEqual(win.input_field.text(), "")


class TestHistoryColors(unittest.TestCase):
    """Tests that history entries render colored results in the UI."""

    def test_history_shows_colored_results(self):
        app = QApplication.instance() or QApplication([])
        win = CalculatorWindow()

        # Add a successful entry
        win.input_field.setText("1+1")
        win._on_enter_pressed()

        # Add an error entry
        win.input_field.setText("1 / 0")
        win._on_enter_pressed()

        html = win.history_browser.toHtml()
        from Keisanbako.constants import COLORS_DARK as COLORS, COLORS_LIGHT

        success_color = COLORS["success"] if win.current_theme == "dark" else COLORS_LIGHT["success_light"]
        error_color = COLORS["error"] if win.current_theme == "dark" else COLORS_LIGHT["error_light"]

        self.assertIn(success_color, html)
        self.assertIn(error_color, html)


class TestCurrencySymbolArithmetic(unittest.TestCase):
    """Tests for arithmetic operations with currency symbols."""

    def test_euro_multiplication(self):
        """Test basic multiplication with Euro symbol."""
        result = ExpressionEvaluator.evaluate("100000€ * 10")
        self.assertFalse(result.is_error)
        self.assertIn("1 000 000", result.value)
        self.assertIn("€", result.value)
        self.assertEqual(result.currency, "EUR")

    def test_dollar_addition(self):
        """Test addition with Dollar symbol."""
        result = ExpressionEvaluator.evaluate("100$ + 50$")
        self.assertFalse(result.is_error)
        self.assertIn("150", result.value)
        self.assertIn("$", result.value)
        self.assertEqual(result.currency, "USD")

    def test_pound_subtraction(self):
        """Test subtraction with Pound symbol."""
        result = ExpressionEvaluator.evaluate("1000£ - 250£")
        self.assertFalse(result.is_error)
        self.assertIn("750", result.value)
        self.assertIn("£", result.value)
        self.assertEqual(result.currency, "GBP")

    def test_yen_division(self):
        """Test division with Yen symbol."""
        result = ExpressionEvaluator.evaluate("1000¥ / 2")
        self.assertFalse(result.is_error)
        self.assertIn("500", result.value)
        self.assertIn("¥", result.value)
        self.assertEqual(result.currency, "JPY")

    def test_complex_expression_with_euro(self):
        """Test complex expression with Euro symbol."""
        result = ExpressionEvaluator.evaluate("(100€ + 50€) * 2")
        self.assertFalse(result.is_error)
        self.assertIn("300", result.value)
        self.assertIn("€", result.value)
        self.assertEqual(result.currency, "EUR")

    def test_currency_with_spaces(self):
        """Test currency symbol handling with spaces."""
        result = ExpressionEvaluator.evaluate("100 € * 10")
        self.assertFalse(result.is_error)
        self.assertIn("1 000", result.value)
        self.assertIn("€", result.value)
        self.assertEqual(result.currency, "EUR")

    def test_multiple_currency_symbols_unsupported(self):
        """Test that multiple different currency symbols are not supported."""
        result = ExpressionEvaluator.evaluate("100€ + 50$")
        # This should fail since we can't mix currencies in arithmetic
        self.assertTrue(result.is_error)

    def test_currency_without_numbers(self):
        """Test that currency symbol without numbers is not processed."""
        result = ExpressionEvaluator.evaluate("€ * 10")
        self.assertTrue(result.is_error)

    def test_rupee_symbol(self):
        """Test multiplication with Rupee symbol."""
        result = ExpressionEvaluator.evaluate("1000₹ / 5")
        self.assertFalse(result.is_error)
        self.assertIn("200", result.value)
        self.assertIn("₹", result.value)
        self.assertEqual(result.currency, "INR")

    def test_won_symbol(self):
        """Test addition with Korean Won symbol."""
        result = ExpressionEvaluator.evaluate("10000₩ + 5000₩")
        self.assertFalse(result.is_error)
        self.assertIn("15 000", result.value)
        self.assertIn("₩", result.value)
        self.assertEqual(result.currency, "KRW")

    def test_symbol_at_beginning(self):
        """Test currency symbol at the beginning of expression."""
        result = ExpressionEvaluator.evaluate("$100000 * 10")
        self.assertFalse(result.is_error)
        self.assertIn("1 000 000", result.value)
        self.assertIn("$", result.value)
        self.assertEqual(result.currency, "USD")

    def test_euro_at_beginning_with_addition(self):
        """Test Euro symbol at the beginning with addition."""
        result = ExpressionEvaluator.evaluate("€50 + €100")
        self.assertFalse(result.is_error)
        self.assertIn("150", result.value)
        self.assertIn("€", result.value)
        self.assertEqual(result.currency, "EUR")

    def test_pound_at_beginning_with_subtraction(self):
        """Test Pound symbol at the beginning with subtraction."""
        result = ExpressionEvaluator.evaluate("£1000 - £250")
        self.assertFalse(result.is_error)
        self.assertIn("750", result.value)
        self.assertIn("£", result.value)
        self.assertEqual(result.currency, "GBP")

    def test_mixed_symbol_positions(self):
        """Test currency symbols at both beginning and end."""
        result = ExpressionEvaluator.evaluate("$100 + 50$")
        self.assertFalse(result.is_error)
        self.assertIn("150", result.value)
        self.assertIn("$", result.value)
        self.assertEqual(result.currency, "USD")


class TestCurrencyConversionWithSymbols(unittest.TestCase):
    """Tests for currency conversion with currency symbols."""

    def test_euro_to_usd_conversion(self):
        """Test Euro symbol in currency conversion."""
        result = ExpressionEvaluator.evaluate("100€ in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_dollar_to_eur_conversion(self):
        """Test Dollar symbol at the beginning of currency conversion."""
        result = ExpressionEvaluator.evaluate("$100 to eur")
        self.assertFalse(result.is_error)
        self.assertIn("EUR", result.value)

    def test_yen_to_usd_conversion(self):
        """Test Yen symbol in currency conversion."""
        result = ExpressionEvaluator.evaluate("100 ¥ in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_pound_to_usd_conversion(self):
        """Test Pound symbol at the beginning of currency conversion."""
        result = ExpressionEvaluator.evaluate("£100 to usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_rupee_to_usd_conversion(self):
        """Test Rupee symbol in currency conversion."""
        result = ExpressionEvaluator.evaluate("1000₹ in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_standard_currency_conversion_still_works(self):
        """Test that standard currency conversion without symbols still works."""
        result = ExpressionEvaluator.evaluate("100 eur in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)


class TestArithmeticCurrencyConversion(unittest.TestCase):
    """Tests for arithmetic expressions with currency conversion."""

    def test_division_with_currency_conversion(self):
        """Test division followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("30000000 / 5 yen in eur")
        self.assertFalse(result.is_error)
        self.assertIn("EUR", result.value)
        # 30000000 / 5 = 6000000 yen, convert to EUR

    def test_multiplication_with_currency_conversion(self):
        """Test multiplication followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("100 * 2 usd in eur")
        self.assertFalse(result.is_error)
        self.assertIn("EUR", result.value)

    def test_addition_with_currency_conversion(self):
        """Test addition followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("1000 + 500 gbp in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_subtraction_with_currency_conversion(self):
        """Test subtraction followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("1000 - 200 eur in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_complex_arithmetic_with_currency_conversion(self):
        """Test complex arithmetic expression followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("(100 + 50) * 2 gbp in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)

    def test_exponent_with_currency_conversion(self):
        """Test exponent followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("2 ** 10 usd in eur")
        self.assertFalse(result.is_error)
        self.assertIn("EUR", result.value)

    def test_division_without_spaces(self):
        """Test arithmetic without spaces followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("30000000/5 yen in eur")
        self.assertFalse(result.is_error)
        self.assertIn("EUR", result.value)

    def test_mixed_operators_with_currency_conversion(self):
        """Test mixed operators followed by currency conversion."""
        result = ExpressionEvaluator.evaluate("100 * 5 + 50 eur in usd")
        self.assertFalse(result.is_error)
        self.assertIn("USD", result.value)


if __name__ == "__main__":
    unittest.main()

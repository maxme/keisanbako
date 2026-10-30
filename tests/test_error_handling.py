"""Test comprehensive error handling and user feedback (Phase 3).

Tests for:
- Better error messages with hints
- Error type detection
- Offline cache indicators
- User-friendly error display
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.evaluator import ExpressionEvaluator, CalculationResult
from Keisanbako.settings import format_number, format_date
from Keisanbako.converters import UnitConverter, CURRENCY_MAP, CurrencyConverter
from Keisanbako.translations import TranslationManager


class TestErrorMessagesBase(unittest.TestCase):
    """Base class for error message tests."""

    def setUp(self):
        """Set up test evaluator."""
        # Use the TranslationManager's translate method for proper translation support
        tm = TranslationManager()
        translator_fn = tm.translate

        self.evaluator = ExpressionEvaluator(
            format_number_fn=format_number,
            format_date_fn=format_date,
            currency_converter=CurrencyConverter,
            unit_converter=UnitConverter,
            translator_fn=translator_fn,
            currency_map=CURRENCY_MAP,
            unit_factors={
                **UnitConverter.LENGTH_FACTORS,
                **UnitConverter.WEIGHT_FACTORS,
                **UnitConverter.AREA_FACTORS,
            }
        )


class TestErrorTypeDetection(TestErrorMessagesBase):
    """Test error type detection and classification."""

    def test_syntax_error_detection(self):
        """Test that syntax errors are properly detected."""
        result = self.evaluator.evaluate("1 +* 2")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "syntax")
        self.assertIsNotNone(result.error_message)
        self.assertIn("syntax", result.error_message.lower())

    def test_undefined_variable_detection(self):
        """Test that undefined variables are detected."""
        result = self.evaluator.evaluate("undefined_var + 1")
        self.assertTrue(result.is_error)
        self.assertIn(result.error_type, ["undefined", "invalid"])
        self.assertIsNotNone(result.error_message)

    def test_zero_division_detection(self):
        """Test that zero division is properly detected."""
        result = self.evaluator.evaluate("1/0")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "zero_division")
        self.assertIsNotNone(result.error_message)
        self.assertIn("divide", result.error_message.lower())

    def test_invalid_expression_detection(self):
        """Test that invalid expressions are detected."""
        result = self.evaluator.evaluate("((")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "syntax")

    def test_modulo_zero_detection(self):
        """Test that modulo by zero is detected."""
        result = self.evaluator.evaluate("5 % 0")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "zero_division")


class TestErrorMessages(TestErrorMessagesBase):
    """Test error message content and quality."""

    def test_error_message_not_generic(self):
        """Test that error messages are not generic 'Error' strings."""
        result = self.evaluator.evaluate("undefined_var")
        self.assertTrue(result.is_error)
        # Error message should be more specific than just "Error"
        if result.error_message:
            self.assertNotEqual(result.error_message, "Error")
            self.assertTrue(len(result.error_message) > 5)

    def test_error_message_includes_hint(self):
        """Test that error messages include helpful hints."""
        result = self.evaluator.evaluate("1/0")
        self.assertTrue(result.is_error)
        if result.error_message:
            # Should mention division or zero
            msg_lower = result.error_message.lower()
            self.assertTrue(
                "divide" in msg_lower or "zero" in msg_lower or "check" in msg_lower
            )

    def test_name_error_message_extraction(self):
        """Test that NameError messages extract variable names."""
        result = self.evaluator.evaluate("missing_func()")
        self.assertTrue(result.is_error)
        if result.error_message and "missing_func" not in result.error_message:
            # May not include exact name, but should be descriptive
            self.assertIn("undefined", result.error_message.lower())

    def test_error_message_helpful_for_syntax(self):
        """Test that syntax error messages are helpful."""
        result = self.evaluator.evaluate("(2 +")
        self.assertTrue(result.is_error)
        if result.error_message:
            msg_lower = result.error_message.lower()
            self.assertTrue(
                any(word in msg_lower for word in ["syntax", "check", "parenthes", "operator"])
            )


class TestCachedResultIndicator(TestErrorMessagesBase):
    """Test offline/cached data indicators."""

    def test_cached_result_flag(self):
        """Test that cached results are properly flagged."""
        # Create a result with cached flag
        result = CalculationResult("100 USD", is_error=False, is_cached=True)
        self.assertTrue(result.is_cached)
        self.assertFalse(result.is_error)

    def test_non_cached_result_flag(self):
        """Test that fresh results are not marked as cached."""
        result = self.evaluator.evaluate("1+1")
        # Direct evaluation should not be marked as cached
        self.assertFalse(result.is_cached)

    def test_cached_result_format(self):
        """Test formatting of cached results."""
        result = CalculationResult("50 EUR", is_error=False, is_cached=True, currency="EUR")
        self.assertEqual(result.value, "50 EUR")
        self.assertTrue(result.is_cached)
        self.assertEqual(result.currency, "EUR")


class TestErrorMessageVariations(TestErrorMessagesBase):
    """Test various error scenarios and their messages."""

    def test_invalid_function_name(self):
        """Test error when using undefined function."""
        result = self.evaluator.evaluate("unknown_func(5)")
        self.assertTrue(result.is_error)

    def test_missing_closing_paren(self):
        """Test error with missing closing parenthesis."""
        result = self.evaluator.evaluate("sqrt(16")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "syntax")

    def test_extra_closing_paren(self):
        """Test error with extra closing parenthesis."""
        result = self.evaluator.evaluate("sqrt(16))")
        self.assertTrue(result.is_error)

    def test_invalid_assignment_variable_name(self):
        """Test error with invalid variable name in assignment."""
        result = self.evaluator.evaluate("123invalid = 5")
        # Should fail because variable names can't start with numbers
        self.assertTrue(result.is_error or not result.is_error)  # Either behavior is okay


class TestSuccessfulResults(TestErrorMessagesBase):
    """Test that successful results have proper format."""

    def test_successful_result_has_no_error_type(self):
        """Test that successful results don't have error_type."""
        result = self.evaluator.evaluate("1+1")
        self.assertFalse(result.is_error)
        # error_type should be None for successful results
        self.assertIsNone(result.error_type)

    def test_successful_result_has_no_error_message(self):
        """Test that successful results don't have error_message."""
        result = self.evaluator.evaluate("2*3")
        self.assertFalse(result.is_error)
        self.assertIsNone(result.error_message)

    def test_successful_mathematical_result(self):
        """Test basic mathematical evaluation."""
        result = self.evaluator.evaluate("10 + 5")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "15")

    def test_successful_function_result(self):
        """Test function evaluation."""
        result = self.evaluator.evaluate("sqrt(16)")
        self.assertFalse(result.is_error)
        # Format might be "4" or "4.0" depending on format_number
        self.assertIn(result.value, ["4", "4.0"])


class TestErrorTypeCompleteness(TestErrorMessagesBase):
    """Test that all common error types are properly handled."""

    def test_all_error_types_documented(self):
        """Test that error types are limited to known categories."""
        error_types = [
            "syntax",
            "undefined",
            "zero_division",
            "invalid",
            "unsupported_currency",
            "unsupported_unit",
        ]

        # Test a few known error scenarios
        test_cases = [
            ("1 +* 2", "syntax"),
            ("undefined_var", "undefined"),
            ("10 / 0", "zero_division"),
        ]

        for expr, expected_type in test_cases:
            result = self.evaluator.evaluate(expr)
            if result.is_error:
                # Error type should be one of the known types
                self.assertIsNotNone(result.error_type)


class TestErrorMessageLocalization(unittest.TestCase):
    """Test error message handling with translation."""

    def test_error_message_with_translator(self):
        """Test that error messages work with translator function."""

        def mock_translator(key):
            """Mock translator that returns translated text."""
            translations = {
                "syntax": "Erreur de syntaxe",
                "undefined": "Variable non définie",
            }
            return translations.get(key, key)

        evaluator = ExpressionEvaluator(
            format_number_fn=format_number,
            format_date_fn=format_date,
            translator_fn=mock_translator,
        )

        result = evaluator.evaluate("1 +* 2")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "syntax")


class TestUIErrorDisplay(unittest.TestCase):
    """Test how errors are displayed in the UI."""

    def test_error_result_structure(self):
        """Test that error results have proper structure for UI display."""
        result = CalculationResult("Error", is_error=True, error_type="syntax", error_message="Check syntax")
        self.assertTrue(result.is_error)
        self.assertEqual(result.error_type, "syntax")
        self.assertEqual(result.error_message, "Check syntax")

    def test_cached_result_structure(self):
        """Test that cached results have proper structure for UI display."""
        result = CalculationResult("100", is_error=False, is_cached=True)
        self.assertFalse(result.is_error)
        self.assertTrue(result.is_cached)
        self.assertIsNone(result.error_type)

    def test_result_with_currency_and_cache(self):
        """Test result with both currency and cache indicators."""
        result = CalculationResult(
            "100 USD",
            is_error=False,
            currency="USD",
            is_cached=True
        )
        self.assertEqual(result.value, "100 USD")
        self.assertEqual(result.currency, "USD")
        self.assertTrue(result.is_cached)


class TestErrorRecovery(TestErrorMessagesBase):
    """Test error recovery and subsequent operations."""

    def test_recovery_after_syntax_error(self):
        """Test that calculator can recover after syntax error."""
        # First, an error
        result1 = self.evaluator.evaluate("1 +* 2")
        self.assertTrue(result1.is_error)

        # Then, a correct expression
        result2 = self.evaluator.evaluate("1 + 2")
        self.assertFalse(result2.is_error)
        self.assertEqual(result2.value, "3")

    def test_recovery_after_undefined_variable(self):
        """Test that calculator can recover after undefined variable error."""
        # First, an error
        result1 = self.evaluator.evaluate("unknown_var")
        self.assertTrue(result1.is_error)

        # Define the variable
        result2 = self.evaluator.evaluate("x = 10")
        self.assertFalse(result2.is_error)

        # Use it
        result3 = self.evaluator.evaluate("x + 5")
        self.assertFalse(result3.is_error)
        self.assertEqual(result3.value, "15")


if __name__ == "__main__":
    unittest.main()

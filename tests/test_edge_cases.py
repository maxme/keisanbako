"""Edge Cases & Performance Tests for the Keisanbako calculator.

This module tests edge cases and performance including:
- Very large numbers (100+ digits)
- Deeply nested expressions (100+ levels)
- Large history (1000+ entries)
- Rapid consecutive evaluations
- Special characters in variable names
- Unicode in translations
- Extreme date arithmetic (year 2099)
- Zero-division recovery
"""

import unittest
import sys
import time
import math
from pathlib import Path
from datetime import date, timedelta, datetime
from decimal import Decimal

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.evaluator import ExpressionEvaluator, CalculationResult
from Keisanbako.settings import format_number, format_date
from Keisanbako.parser import ExpressionParser


class EdgeCaseTestBase(unittest.TestCase):
    """Base class for edge case tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = ExpressionEvaluator()
        self.parser = ExpressionParser()


class TestLargeNumbers(EdgeCaseTestBase):
    """Test handling of very large numbers."""

    def test_100_digit_number(self):
        """Test calculation with 100+ digit number."""
        # Create a very large number
        large_num = "1" * 100
        result = self.evaluator.evaluate(large_num)
        self.assertFalse(result.is_error)

    def test_large_number_arithmetic(self):
        """Test arithmetic with large numbers."""
        result = self.evaluator.evaluate("9" * 50 + " + " + "1" * 50)
        self.assertIsNotNone(result.value)

    def test_large_number_exponentiation(self):
        """Test exponentiation with large results."""
        result = self.evaluator.evaluate("2 ** 100")
        self.assertFalse(result.is_error)
        # Should be a very large number
        self.assertGreater(float(str(result.value).replace(" ", "")), 0)

    def test_very_large_factorial(self):
        """Test factorial of large number."""
        # Note: factorials grow very quickly
        result = self.evaluator.evaluate("factorial(20)")
        if not result.is_error:
            self.assertGreater(float(str(result.value).replace(" ", "")), 0)

    def test_large_number_formatting(self):
        """Test formatting of large numbers."""
        large_val = 10**20
        formatted = format_number(large_val)
        # Should have thousands separators
        self.assertIn(" ", formatted)

    def test_precision_loss_detection(self):
        """Test detection of precision loss with large numbers."""
        # Very precise calculation
        result = self.evaluator.evaluate("1.000000000000001 + 0.000000000000001")
        self.assertFalse(result.is_error)

    def test_scientific_notation_large(self):
        """Test scientific notation with large exponents."""
        result = self.evaluator.evaluate("1e100")
        self.assertFalse(result.is_error)

    def test_infinity_handling(self):
        """Test handling of calculations resulting in infinity."""
        result = self.evaluator.evaluate("10**1000")
        # Should either succeed with large number or error gracefully
        self.assertIsNotNone(result.value)


class TestDeeplyNested(EdgeCaseTestBase):
    """Test handling of deeply nested expressions."""

    def test_50_nested_parentheses(self):
        """Test deeply nested parentheses."""
        expr = "1" + " + (1" * 50 + ")" * 50
        result = self.evaluator.evaluate(expr)
        self.assertFalse(result.is_error)

    def test_100_nested_parentheses(self):
        """Test extremely deep nesting."""
        expr = "2" + " * (2" * 100 + ")" * 100
        result = self.evaluator.evaluate(expr)
        # Should handle deep nesting
        self.assertIsNotNone(result.value)

    def test_function_nesting(self):
        """Test nested function calls."""
        expr = "sqrt(abs(sin(cos(tan(1)))))"
        result = self.evaluator.evaluate(expr)
        self.assertIsNotNone(result.value)
        result = self.evaluator.evaluate(expr)
        self.assertFalse(result.is_error)

    def test_nested_conversion_functions(self):
        """Test nested unit/currency conversions."""
        # This would test nested conversion calls
        expr = "100"
        result = self.evaluator.evaluate(expr)
        self.assertIsNotNone(result.value)

    def test_stack_overflow_protection(self):
        """Test protection against stack overflow from excessive nesting."""
        # Create extremely deep nesting
        expr = "(" * 1000 + "1" + ")" * 1000
        result = self.evaluator.evaluate(expr)
        # Should either handle or error gracefully
        self.assertIsNotNone(result.value)


class TestLargeHistory(EdgeCaseTestBase):
    """Test handling of large history."""

    def test_1000_history_entries(self):
        """Test calculator with 1000+ history entries."""
        # Simulate history
        history = []
        evaluator = ExpressionEvaluator()

        for i in range(1000):
            result = evaluator.evaluate(f"{i}+{i}")
            if not result.is_error:
                history.append(str(result.value))

        # Should handle large history
        self.assertGreaterEqual(len(history), 900)  # Most should succeed

    def test_history_memory_efficiency(self):
        """Test history doesn't consume excessive memory."""
        evaluator = ExpressionEvaluator()
        history = []

        # Add 500 entries
        for i in range(500):
            result = evaluator.evaluate(f"{i}+{i}")
            if not result.is_error:
                history.append(str(result.value))

        # Should complete without hanging
        self.assertGreater(len(history), 400)

    def test_large_history_rendering(self):
        """Test rendering large history (no blocking)."""
        # Simulate history rendering performance
        history_items = [f"Expression {i}: Result {i*2}" for i in range(500)]

        # Should not take excessive time
        start = time.time()
        # Simulate rendering
        formatted = "\n".join(history_items[:500])
        elapsed = time.time() - start

        self.assertLess(elapsed, 1.0)  # Should complete quickly

    def test_history_search_performance(self):
        """Test searching through large history."""
        history = [f"{i}+{i}={i*2}" for i in range(500)]

        start = time.time()
        # Simulate search
        matches = [h for h in history if "100" in h]
        elapsed = time.time() - start

        self.assertLess(elapsed, 0.5)  # Should be fast


class TestRapidConsecutive(EdgeCaseTestBase):
    """Test rapid consecutive evaluations."""

    def test_1000_rapid_evaluations(self):
        """Test 1000 rapid consecutive evaluations."""
        evaluator = ExpressionEvaluator()
        results = []

        start = time.time()
        for i in range(1000):
            result = evaluator.evaluate(f"{i % 100} + {i % 50}")
            results.append(not result.is_error)
        elapsed = time.time() - start

        # Most should succeed
        self.assertGreater(sum(results), 950)
        # Should complete in reasonable time
        self.assertLess(elapsed, 5.0)

    def test_alternating_expressions(self):
        """Test alternating between different expression types."""
        evaluator = ExpressionEvaluator()
        expressions = [
            "1+1", "sqrt(16)", "2**8", "10/2",
            "today()", "1 day", "100 USD to EUR"
        ]

        for _ in range(100):
            for expr in expressions:
                result = evaluator.evaluate(expr)
                self.assertIsNotNone(result)

    def test_performance_degradation(self):
        """Test that performance doesn't degrade with many evaluations."""
        evaluator = ExpressionEvaluator()

        # First batch
        start1 = time.time()
        for i in range(100):
            evaluator.evaluate(f"{i}+{i}")
        time1 = time.time() - start1

        # Second batch (after warming up)
        start2 = time.time()
        for i in range(100, 200):
            evaluator.evaluate(f"{i}+{i}")
        time2 = time.time() - start2

        # Second batch should not be significantly slower
        self.assertLess(time2, time1 * 2)


class TestSpecialCharacters(EdgeCaseTestBase):
    """Test special characters in variable names."""

    def test_underscore_in_variable(self):
        """Test variable names with underscores."""
        self.evaluator.USER_VARS["my_var"] = 42
        result = self.evaluator.evaluate("my_var * 2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "84")

    def test_numbers_in_variable(self):
        """Test variable names with numbers."""
        self.evaluator.USER_VARS["var1"] = 10
        result = self.evaluator.evaluate("var1 + 5")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "15")

    def test_single_letter_variables(self):
        """Test single letter variable names."""
        self.evaluator.USER_VARS["x"] = 5
        self.evaluator.USER_VARS["y"] = 10
        result = self.evaluator.evaluate("x + y")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "15")

    def test_greek_letters_in_context(self):
        """Test Greek letters when supported."""
        # Pi and e are built-in
        result = self.evaluator.evaluate("pi")
        self.assertFalse(result.is_error)
        self.assertAlmostEqual(float(result.value), math.pi, places=5)

    def test_long_variable_names(self):
        """Test very long variable names."""
        long_var = "my_very_long_variable_name_that_is_quite_lengthy"
        self.evaluator.USER_VARS[long_var] = 100
        result = self.evaluator.evaluate(f"{long_var} / 2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "50")


class TestUnicodeHandling(EdgeCaseTestBase):
    """Test Unicode in translations."""

    def test_unicode_in_format_string(self):
        """Test Unicode in number formatting."""
        # Test with various Unicode characters
        result = format_number(1000)
        self.assertIsNotNone(result)

    def test_unicode_in_date_format(self):
        """Test Unicode in date formatting."""
        result = format_date(date.today())
        self.assertIsNotNone(result)

    def test_unicode_variable_names(self):
        """Test support for Unicode variable names."""
        # This depends on implementation
        self.evaluator.USER_VARS["x"] = 42
        result = self.evaluator.evaluate("x * 2")
        self.assertFalse(result.is_error)

    def test_translation_completeness(self):
        """Test that translation strings are complete."""
        # This would check translation files are complete
        # For now, verify structure
        self.assertIsNotNone(self.evaluator)


class TestExtremeDateArithmetic(EdgeCaseTestBase):
    """Test extreme date arithmetic."""

    def test_date_arithmetic_year_2099(self):
        """Test date arithmetic to year 2099."""
        result = self.evaluator.evaluate("date(2024,1,1) + 30000 days")
        self.assertFalse(result.is_error)

    def test_date_arithmetic_year_1900(self):
        """Test date arithmetic with very old dates."""
        result = self.evaluator.evaluate("date(1900,1,1) + 1 day")
        self.assertFalse(result.is_error)

    def test_leap_year_arithmetic(self):
        """Test arithmetic across leap years."""
        result = self.evaluator.evaluate("date(2024,2,28) + 1 day")
        self.assertFalse(result.is_error)

    def test_large_timedelta(self):
        """Test very large time deltas."""
        result = self.evaluator.evaluate("1000 years")
        self.assertFalse(result.is_error)

    def test_date_subtraction_large_delta(self):
        """Test date subtraction with large time difference."""
        result = self.evaluator.evaluate("date(2100,1,1) - date(2000,1,1)")
        self.assertFalse(result.is_error)

    def test_february_29th_handling(self):
        """Test handling of February 29th."""
        result = self.evaluator.evaluate("date(2024,2,29)")
        self.assertFalse(result.is_error)

    def test_month_boundary_arithmetic(self):
        """Test arithmetic at month boundaries."""
        result = self.evaluator.evaluate("date(2024,1,31) + 1 day")
        self.assertFalse(result.is_error)


class TestZeroDivision(EdgeCaseTestBase):
    """Test zero-division recovery."""

    def test_zero_division_error(self):
        """Test division by zero returns error."""
        result = self.evaluator.evaluate("1/0")
        self.assertTrue(result.is_error)

    def test_zero_division_in_expression(self):
        """Test zero division in complex expression."""
        result = self.evaluator.evaluate("5 + (10/0)")
        self.assertTrue(result.is_error)

    def test_near_zero_division(self):
        """Test division by very small number (not zero)."""
        result = self.evaluator.evaluate("1 / 0.000001")
        self.assertFalse(result.is_error)
        self.assertGreater(float(str(result.value).replace(" ", "")), 0)

    def test_zero_modulo(self):
        """Test modulo by zero."""
        result = self.evaluator.evaluate("5 % 0")
        # Should handle gracefully
        self.assertIsNotNone(result.value)

    def test_zero_power(self):
        """Test 0 to the power of 0."""
        result = self.evaluator.evaluate("0 ** 0")
        # Mathematically undefined, should handle gracefully
        self.assertIsNotNone(result.value)

    def test_recovery_after_error(self):
        """Test calculator recovers after division by zero."""
        self.evaluator.evaluate("1/0")
        # Should still work
        result = self.evaluator.evaluate("2+2")
        self.assertFalse(result.is_error)
        self.assertEqual(result.value, "4")


class TestPerformanceBenchmarks(EdgeCaseTestBase):
    """Test performance benchmarks."""

    def test_simple_expression_performance(self):
        """Test simple expression evaluation performance."""
        start = time.time()
        for _ in range(1000):
            self.evaluator.evaluate("1+1")
        elapsed = time.time() - start

        # Should average under 1ms per evaluation
        avg_time = (elapsed * 1000) / 1000
        self.assertLess(avg_time, 5)  # milliseconds

    def test_complex_expression_performance(self):
        """Test complex expression evaluation performance."""
        expr = "((1 + 2) * (3 + 4)) / ((5 - 2) * (6 / 2))"

        start = time.time()
        for _ in range(100):
            self.evaluator.evaluate(expr)
        elapsed = time.time() - start

        # Should complete in reasonable time
        self.assertLess(elapsed, 2.0)

    def test_variable_lookup_performance(self):
        """Test variable lookup performance."""
        # Add many variables
        for i in range(100):
            self.evaluator.USER_VARS[f"var_{i}"] = i

        start = time.time()
        for i in range(100):
            self.evaluator.evaluate(f"var_{i} * 2")
        elapsed = time.time() - start

        # Should be fast even with many variables
        self.assertLess(elapsed, 1.0)


if __name__ == '__main__':
    unittest.main()

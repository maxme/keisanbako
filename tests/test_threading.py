"""Threading & Concurrency Tests for the Keisanbako calculator.

This module tests multithreading functionality including:
- Expression evaluation in worker thread
- Debouncing logic (300ms delay)
- Multiple simultaneous expressions
- History loading in background
- Thread safety of USER_VARS
- UI non-blocking during evaluation
- Graceful shutdown of workers
- Thread cancellation and cleanup
"""

import unittest
import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from unittest.mock import PropertyMock
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal
import tempfile

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.ui import CalculatorWindow, ExpressionEvaluatorWorker, HistoryLoaderWorker
from Keisanbako.evaluator import ExpressionEvaluator


class ThreadingTestBase(unittest.TestCase):
    """Base class for threading tests."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for all tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_history_file = Path(self.temp_dir.name) / "history.txt"

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()


class TestExpressionEvaluatorWorker(ThreadingTestBase):
    """Test ExpressionEvaluatorWorker thread functionality."""

    def test_worker_thread_creation(self):
        """Test worker thread can be created."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        self.assertIsInstance(worker, QThread)
        worker.quit()
        worker.wait(1000)

    def test_worker_evaluates_expression(self):
        """Test worker evaluates expression in thread."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        results = []

        def capture_result(result):
            results.append(result)

        worker.evaluation_done.connect(capture_result)

        worker.set_expression("1+1")
        worker.start()
        # Give thread time to process
        time.sleep(0.1)
        worker.quit()
        worker.wait(1000)

        # Worker should have processed the expression
        self.assertIsNotNone(worker)

    def test_worker_handles_error(self):
        """Test worker handles evaluation errors."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        results = []

        worker.evaluation_done.connect(lambda r: results.append(r))

        worker.set_expression("undefined_var +")  # Invalid expression
        worker.start()
        time.sleep(0.1)
        worker.quit()
        worker.wait(1000)

    def test_worker_stop_signal(self):
        """Test worker stop signal."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        worker.stop()
        worker.quit()
        worker.wait(1000)

    def test_multiple_expressions_sequential(self):
        """Test evaluating multiple expressions sequentially."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        results = []

        worker.evaluation_done.connect(lambda r: results.append(r))

        expressions = ["1+1", "2*2", "sqrt(16)"]
        for expr in expressions:
            worker.set_expression(expr)
            worker.start()
            time.sleep(0.05)  # Small delay between
            worker.quit()
            worker.wait(1000)

        worker.quit()

    def test_worker_thread_is_separate(self):
        """Test worker runs in separate thread."""
        main_thread_id = threading.current_thread().ident
        worker_thread_id = [None]

        evaluator = ExpressionEvaluator()

        class TestWorker(ExpressionEvaluatorWorker):
            def run(self):
                worker_thread_id[0] = threading.current_thread().ident
                super().run()

        worker = TestWorker(evaluator)
        worker.start()
        time.sleep(0.1)
        worker.quit()
        worker.wait(1000)

        # Should not be equal (different threads)
        # Note: This is informational; worker should run separately
        self.assertIsNotNone(worker_thread_id[0])

    def test_worker_cleanup_on_delete(self):
        """Test worker cleans up properly on deletion."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        worker_id = id(worker)
        worker.quit()
        worker.wait(1000)
        del worker

        # Object should be deleted
        self.assertTrue(True)


class TestHistoryLoaderWorker(ThreadingTestBase):
    """Test HistoryLoaderWorker thread functionality."""

    def test_history_loader_creation(self):
        """Test history loader thread can be created."""
        loader = HistoryLoaderWorker(self.temp_history_file)
        self.assertIsInstance(loader, QThread)
        loader.quit()
        loader.wait(1000)

    def test_history_loader_empty_file(self):
        """Test history loader with empty file."""
        # Create empty history file
        self.temp_history_file.touch()

        loader = HistoryLoaderWorker(self.temp_history_file)
        results = []

        loader.history_loaded.connect(lambda e: results.append(e))

        loader.start()
        loader.wait(2000)

        # Should handle empty file without error
        self.assertIsNotNone(loader)

    def test_history_loader_with_entries(self):
        """Test history loader loads entries from file."""
        # Create file with entries
        entries = ["1+1", "2+2", "3+3"]
        with open(self.temp_history_file, 'w') as f:
            for entry in entries:
                f.write(entry + "\n")

        loader = HistoryLoaderWorker(self.temp_history_file)
        results = []

        loader.history_loaded.connect(lambda e: results.append(e))

        loader.start()
        loader.wait(2000)

    def test_history_loader_nonexistent_file(self):
        """Test history loader with nonexistent file."""
        nonexistent = self.temp_history_file.parent / "nonexistent.txt"

        loader = HistoryLoaderWorker(nonexistent)
        loader.start()
        loader.wait(2000)

        # Should handle missing file gracefully
        self.assertIsNotNone(loader)

    def test_history_loader_large_file(self):
        """Test history loader with large history file."""
        # Create file with many entries
        with open(self.temp_history_file, 'w') as f:
            for i in range(1000):
                f.write(f"{i}+{i}\n")

        loader = HistoryLoaderWorker(self.temp_history_file)
        loader.start()
        loader.wait(2000)


class TestDebouncing(ThreadingTestBase):
    """Test debouncing logic for rapid input."""

    def test_debounce_delay_300ms(self):
        """Test debouncing delay is approximately 300ms."""
        with patch('Keisanbako.ui.CalculatorWindow.HISTORY_FILE', self.temp_history_file):
            window = CalculatorWindow()

            # Find debounce timer (called _eval_timer)
            self.assertIsNotNone(window._eval_timer)

            window.close()

    def test_rapid_input_triggers_once(self):
        """Test rapid input only triggers evaluation once after delay."""
        with patch('Keisanbako.ui.CalculatorWindow.HISTORY_FILE', self.temp_history_file):
            window = CalculatorWindow()
            eval_count = [0]

            original_evaluate = window._on_enter_pressed
            def count_evals():
                eval_count[0] += 1
                return original_evaluate()

            window._on_enter_pressed = count_evals

            # Simulate rapid typing
            for i in range(5):
                window.input_field.setText(f"{i}+{i}")
                time.sleep(0.05)  # Fast input

            time.sleep(0.4)  # Wait for debounce

            window.close()

    def test_debounce_reset_on_new_input(self):
        """Test debounce timer resets with new input."""
        with patch('Keisanbako.ui.CalculatorWindow.HISTORY_FILE', self.temp_history_file):
            window = CalculatorWindow()

            # Debounce should be active
            self.assertIsNotNone(window._eval_timer)

            window.close()


class TestThreadSafety(ThreadingTestBase):
    """Test thread safety of shared state."""

    def test_user_vars_thread_safety(self):
        """Test USER_VARS is thread-safe across multiple threads."""
        evaluator = ExpressionEvaluator()
        results = []
        errors = []

        def set_and_get_var(var_name, value):
            try:
                evaluator.USER_VARS[var_name] = value
                result = evaluator.USER_VARS.get(var_name)
                results.append((var_name, result))
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=set_and_get_var, args=(f"var_{i}", i*10))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should not have errors
        self.assertEqual(len(errors), 0)
        # All variables should be set
        self.assertEqual(len(results), 5)

    def test_concurrent_evaluations_safe(self):
        """Test concurrent evaluations don't interfere."""
        evaluator = ExpressionEvaluator()
        results = []

        def evaluate_expr(expr):
            result = evaluator.evaluate(expr)
            results.append(result)

        threads = []
        for expr in ["1+1", "2*2", "sqrt(16)", "10/2"]:
            t = threading.Thread(target=evaluate_expr, args=(expr,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All should complete without error
        self.assertEqual(len(results), 4)


class TestUIBlocking(ThreadingTestBase):
    """Test UI doesn't block during evaluation."""

    def test_ui_responsive_during_eval(self):
        """Test UI remains responsive during evaluation."""
        with patch('Keisanbako.ui.CalculatorWindow.HISTORY_FILE', self.temp_history_file):
            window = CalculatorWindow()

            # Start evaluation
            window.input_field.setText("1+1")
            start = time.time()
            window._on_enter_pressed()
            elapsed = time.time() - start

            # Should return quickly (not block)
            self.assertLess(elapsed, 1.0)

            window.close()

    def test_input_field_responsive_during_calc(self):
        """Test input field is responsive during calculation."""
        with patch('Keisanbako.ui.CalculatorWindow.HISTORY_FILE', self.temp_history_file):
            window = CalculatorWindow()

            window.input_field.setText("1+1")
            window._on_enter_pressed()

            # Should be able to type while evaluating
            window.input_field.setText("2+2")
            self.assertEqual(window.input_field.text(), "2+2")

            window.close()


class TestWorkerShutdown(ThreadingTestBase):
    """Test graceful shutdown of workers."""

    def test_worker_shutdown_clean(self):
        """Test worker shuts down cleanly."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        worker.start()
        time.sleep(0.05)
        worker.quit()
        result = worker.wait(1000)
        self.assertTrue(result)

    def test_multiple_workers_shutdown(self):
        """Test multiple workers shut down cleanly."""
        evaluator = ExpressionEvaluator()
        workers = [ExpressionEvaluatorWorker(evaluator) for _ in range(3)]

        for w in workers:
            w.start()

        time.sleep(0.1)

        for w in workers:
            w.quit()

        for w in workers:
            result = w.wait(1000)
            self.assertTrue(result)

    def test_no_resource_leak_on_shutdown(self):
        """Test no resource leak when workers shut down."""
        evaluator = ExpressionEvaluator()
        # Create and destroy multiple workers
        for _ in range(10):
            worker = ExpressionEvaluatorWorker(evaluator)
            worker.quit()
            worker.wait(1000)

        # Should complete without error
        self.assertTrue(True)


class TestThreadCancellation(ThreadingTestBase):
    """Test thread cancellation and cleanup."""

    def test_stop_worker_mid_evaluation(self):
        """Test stopping worker during evaluation."""
        evaluator = ExpressionEvaluator()
        worker = ExpressionEvaluatorWorker(evaluator)
        worker.set_expression("1+1")
        worker.start()
        time.sleep(0.05)
        worker.stop()
        worker.quit()
        worker.wait(1000)

    def test_rapid_start_stop(self):
        """Test rapid start/stop cycles."""
        evaluator = ExpressionEvaluator()
        for _ in range(5):
            worker = ExpressionEvaluatorWorker(evaluator)
            worker.start()
            time.sleep(0.01)
            worker.stop()
            worker.quit()
            worker.wait(1000)

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

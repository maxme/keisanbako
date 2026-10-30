"""Background worker threads for the Keisanbako calculator.

Handles asynchronous operations like expression evaluation and history loading
to keep the UI responsive.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from .evaluator import ExpressionEvaluator, CalculationResult

logger = logging.getLogger(__name__)


class ExpressionEvaluatorWorker(QThread):
    """Worker thread for background expression evaluation to avoid blocking the UI."""

    evaluation_done = Signal(object)  # Emits CalculationResult

    def __init__(self, evaluator: ExpressionEvaluator) -> None:
        """Initialize the worker thread.

        Args:
            evaluator: The ExpressionEvaluator instance to use for evaluation
        """
        super().__init__()
        self.evaluator = evaluator
        self.expression = ""
        self.should_stop = False

    def set_expression(self, expression: str) -> None:
        """Set the expression to evaluate."""
        self.expression = expression

    def run(self) -> None:
        """Evaluate the expression in the background thread."""
        if not self.should_stop:
            result = self.evaluator.evaluate(self.expression)
            if not self.should_stop:
                self.evaluation_done.emit(result)

    def stop(self) -> None:
        """Signal the worker to stop."""
        self.should_stop = True


class HistoryLoaderWorker(QThread):
    """Worker thread for loading history in the background to avoid blocking startup."""

    history_loaded = Signal(list)  # Emits history_entries

    def __init__(self, history_file: Path) -> None:
        """Initialize the history loader worker.

        Args:
            history_file: Path to the history JSON file
        """
        super().__init__()
        self.history_file = history_file
        self.entries: list[str] = []

    def run(self) -> None:
        """Load history from file in the background thread."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    entries = data.get("entries", [])
                    if entries:
                        self.entries = entries
            self.history_loaded.emit(self.entries)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Failed to load history: %s", e)
            self.history_loaded.emit([])

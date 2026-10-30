"""PySide6 UI components for the calculator.

This module handles the main calculator window and UI initialization.
"""

import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QEvent, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QAction, QIcon, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .evaluator import ExpressionEvaluator, CalculationResult
from .settings import SettingsManager, format_number, format_date
from .converters import CurrencyConverter, UnitConverter, RequestCache, CURRENCY_MAP
from .translations import get_translator, t, set_language
from .settings_dialog import SettingsDialog
from .workers import ExpressionEvaluatorWorker, HistoryLoaderWorker
from .themes import (
    ThemeType,
    get_theme_colors,
    apply_history_browser_style,
    apply_input_field_style,
    apply_result_label_style,
    apply_result_label_style_error,
    get_clear_button_stylesheet,
    get_status_bar_stylesheet,
    generate_history_html,
)
from .constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FONT_NAME,
    FONT_FAMILIES,
    FONT_SIZE_HISTORY,
    FONT_SIZE_INPUT,
    FONT_SIZE_RESULT,
    DEBOUNCE_DELAY_MS,
    REQUEST_CACHE_TTL_SECONDS,
    THEME_APPLY_DELAY_MS,
    ICON_LOAD_DELAY_MS,
    HISTORY_FILE,
    CLEAR_BUTTON_WIDTH,
    CLEAR_BUTTON_MARGIN_RIGHT,
    INPUT_FIELD_MIN_HEIGHT,
    RESULT_LABEL_MIN_HEIGHT,
)

logger = logging.getLogger(__name__)


class CalculatorWindow(QMainWindow):
    """Main calculator window."""

    HISTORY_FILE: Path = HISTORY_FILE  # class attr allows test patching

    def __init__(self) -> None:
        """Initialize the calculator window."""
        super().__init__()

        # Initialize settings and language
        language = SettingsManager.get().settings.get("language", "en")
        set_language(language)

        # Create evaluator with dependencies
        self.evaluator: ExpressionEvaluator = ExpressionEvaluator(
            format_number_fn=format_number,
            format_date_fn=format_date,
            currency_converter=CurrencyConverter,
            unit_converter=UnitConverter,
            translator_fn=t,
            currency_map=CURRENCY_MAP,
            unit_factors={**UnitConverter.LENGTH_FACTORS, **UnitConverter.WEIGHT_FACTORS, **UnitConverter.AREA_FACTORS}
        )

        self.history_visible: bool = True
        self.history_browser: QTextBrowser
        self.input_field: QLineEdit
        self.result_label: QLabel
        self.clear_btn: QPushButton
        raw_theme = SettingsManager.get().settings.get("theme", "dark")
        self.current_theme: ThemeType = raw_theme if raw_theme in ("dark", "light") else "dark"

        # Input history state (for up/down navigation)
        self._history_entries: list[str] = []
        self._history_index: Optional[int] = None
        self._history_temp_buffer: Optional[str] = None

        # Background evaluation thread
        self._evaluator_worker: Optional[ExpressionEvaluatorWorker] = None

        # Debouncing timer for input evaluation
        self._eval_timer: QTimer = QTimer()
        self._eval_timer.setSingleShot(True)
        self._eval_timer.timeout.connect(self._evaluate_deferred)
        self._deferred_text: str = ""

        # Request deduplication cache
        self._request_cache: RequestCache = RequestCache(ttl_seconds=REQUEST_CACHE_TTL_SECONDS)
        CurrencyConverter.set_request_cache(self._request_cache)

        self._setup_ui()
        # Defer theme application to after UI is set up to avoid blocking startup
        QTimer.singleShot(THEME_APPLY_DELAY_MS, lambda: self._apply_theme(self.current_theme))

        # Load history in background thread to avoid blocking UI startup
        self._history_loader: HistoryLoaderWorker = HistoryLoaderWorker(self.HISTORY_FILE)
        self._history_loader.history_loaded.connect(self._on_history_loaded)
        self._history_loader.start()

        # Ensure history is scrolled to the bottom once the event loop runs
        QTimer.singleShot(0, self._scroll_history_to_bottom)
        # Set focus on the input field when the app starts
        self.input_field.setFocus()

    def _on_history_loaded(self, entries: list[str]) -> None:
        """Handle history loaded from background thread."""
        self._history_entries = entries
        if entries:
            self._render_history()
            # Scroll to the bottom after history is rendered
            QTimer.singleShot(10, self._scroll_history_to_bottom)

    @property
    def _history_list(self) -> list[str]:
        """Expressions extracted from history entries for navigation."""
        return [e.split(" = ", 1)[0] if " = " in e else e for e in self._history_entries]

    @_history_list.setter
    def _history_list(self, value: list[str]) -> None:
        self._history_entries = value

    def _setup_ui(self) -> None:
        """Initialize and configure the UI."""
        translator = get_translator()
        self.setWindowTitle(translator("window_title_macos"))
        # Defer icon loading to after window is shown to avoid blocking startup
        QTimer.singleShot(ICON_LOAD_DELAY_MS, self._set_window_icon)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self._build_menu_bar()
        self.statusBar().setStyleSheet(get_status_bar_stylesheet(self.current_theme))

        # Main vertical layout: history on top, input on bottom
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # History display
        self._setup_history_display(layout)

        # Input and result area
        self._setup_input_area(layout)

    def _build_menu_bar(self) -> None:
        """Build (or rebuild) the menu bar with current translations."""
        translator = get_translator()
        menubar = self.menuBar()
        menubar.clear()

        file_menu = menubar.addMenu(translator("menu_file"))
        export_action = QAction(translator("action_export_history"), self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_history_dialog)
        file_menu.addAction(export_action)
        clear_action = QAction(translator("action_clear_history"), self)
        clear_action.triggered.connect(self._clear_history)
        file_menu.addAction(clear_action)
        file_menu.addSeparator()
        exit_action = QAction(translator("action_exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu(translator("menu_settings"))
        settings_action = QAction(translator("action_settings"), self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)
        toggle_theme_action = QAction(translator("theme_toggle"), self)
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_theme_action.triggered.connect(self._toggle_theme)
        settings_menu.addAction(toggle_theme_action)

        help_menu = menubar.addMenu(translator("menu_help"))
        help_action = QAction(translator("action_help"), self)
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
        toggle_history_action = QAction(translator("action_toggle_history"), self)
        toggle_history_action.setShortcut(QKeySequence("Ctrl+H"))
        toggle_history_action.triggered.connect(self._toggle_history)
        help_menu.addAction(toggle_history_action)

    def _setup_history_display(self, parent_layout: QVBoxLayout) -> None:
        """Setup the history text browser."""
        self.history_browser = QTextBrowser()
        font = QFont()
        font.setFamilies(FONT_FAMILIES)
        font.setPointSize(FONT_SIZE_HISTORY)
        self.history_browser.setFont(font)
        apply_history_browser_style(self.history_browser, self.current_theme)
        self.history_browser.setOpenLinks(False)
        self.history_browser.anchorClicked.connect(self._on_history_entry_clicked)

        # Floating Clear button overlayed on the history pane
        self.clear_btn = QPushButton(t("action_clear_history"))
        self.clear_btn.setFixedWidth(CLEAR_BUTTON_WIDTH)
        self.clear_btn.clicked.connect(self._clear_history)
        self.clear_btn.setStyleSheet(get_clear_button_stylesheet(self.current_theme))
        self.clear_btn.setVisible(False)  # hidden until there is history to clear

        # Add the browser first so the button can float on top of it
        parent_layout.addWidget(self.history_browser)
        self.history_browser.setParent(self.history_browser.parent())
        self.history_browser.setContentsMargins(0, 0, 0, 0)

        self.clear_btn.setParent(self.history_browser)
        self.clear_btn.raise_()
        self._reposition_clear_button()

        # Install event filter to reposition button on resize
        self.history_browser.installEventFilter(self)

    def _reposition_clear_button(self) -> None:
        """Reposition the clear button to stick to the right of the history browser."""
        self.clear_btn.move(self.history_browser.width() - self.clear_btn.width() - CLEAR_BUTTON_MARGIN_RIGHT, 10)

    def _setup_input_area(self, parent_layout: QVBoxLayout) -> None:
        """Setup the input field and result label."""
        # Input field
        self.input_field = QLineEdit()
        input_font = QFont()
        input_font.setFamilies(FONT_FAMILIES)
        input_font.setPointSize(FONT_SIZE_INPUT)
        self.input_field.setFont(input_font)
        self.input_field.setPlaceholderText(t("input_placeholder"))
        self.input_field.setMinimumHeight(INPUT_FIELD_MIN_HEIGHT)
        apply_input_field_style(self.input_field, self.current_theme)
        self.input_field.textEdited.connect(self._on_text_changed)
        self.input_field.returnPressed.connect(self._on_enter_pressed)
        # Install event filter to capture Up/Down arrows for history navigation
        self.input_field.installEventFilter(self)
        parent_layout.addWidget(self.input_field)

        # Result label (below input field for stable layout)
        self.result_label = QLabel("= ")
        result_font = QFont()
        result_font.setFamilies(FONT_FAMILIES)
        result_font.setPointSize(FONT_SIZE_RESULT)
        result_font.setWeight(QFont.Weight.Bold)
        self.result_label.setFont(result_font)
        apply_result_label_style(self.result_label, self.current_theme)
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(RESULT_LABEL_MIN_HEIGHT)
        self.result_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        parent_layout.addWidget(self.result_label)

    def _set_window_icon(self) -> None:
        """Set the application window icon based on the platform."""
        # Determine icon path based on platform
        if sys.platform == "darwin":  # macOS
            icon_name = "keisanbako.icns"
            icon_dir = "macos"
        elif sys.platform == "win32":  # Windows
            icon_name = "keisanbako.ico"
            icon_dir = "windows"
        else:  # Linux and others
            icon_name = "keisanbako_256x256.png"
            icon_dir = "linux"

        # Try to locate the icon in the resources directory
        icon_path = None

        try:
            # Strategy 1: Use Keisanbako package __path__ (works in Nuitka)
            try:
                import Keisanbako
                if hasattr(Keisanbako, '__path__'):
                    pkg_path = Path(Keisanbako.__path__[0])
                    icon_path = pkg_path / "resources" / icon_dir / icon_name
                    if icon_path.exists():
                        logger.debug(f"Found icon using package path: {icon_path}")
            except:
                pass

            # Strategy 2: Relative to __file__
            if not icon_path or not icon_path.exists():
                package_dir = Path(__file__).parent
                icon_path = package_dir / "resources" / icon_dir / icon_name
                if icon_path.exists():
                    logger.debug(f"Found icon using __file__ path: {icon_path}")

            # Strategy 3: Fallback to development project root
            if not icon_path or not icon_path.exists():
                project_root = Path(__file__).parent.parent.parent
                icon_path = project_root / "src" / "Keisanbako" / "resources" / icon_dir / icon_name
                if icon_path.exists():
                    logger.debug(f"Found icon using project root path: {icon_path}")

            if icon_path and icon_path.exists():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    logger.debug(f"Window icon set from: {icon_path}")
                else:
                    logger.warning(f"Icon loaded but appears invalid: {icon_path}")
            else:
                logger.debug(f"Icon not found at: {icon_path}")
        except Exception as e:
            logger.debug(f"Failed to set window icon: {e}")

    def _apply_theme(self, theme: ThemeType) -> None:
        """Apply UI theme: 'dark' or 'light'."""
        self.current_theme = theme
        bg = get_theme_colors(theme).background
        self.centralWidget().setStyleSheet(f"background-color: {bg};")
        apply_history_browser_style(self.history_browser, theme)
        apply_input_field_style(self.input_field, theme)
        apply_result_label_style(self.result_label, theme)
        self.clear_btn.setStyleSheet(get_clear_button_stylesheet(theme))
        self.statusBar().setStyleSheet(get_status_bar_stylesheet(theme))

    def _toggle_theme(self) -> None:
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(self.current_theme)
        SettingsManager.get().update({"theme": self.current_theme})

    def _toggle_history(self) -> None:
        self.history_visible = not self.history_visible
        self.history_browser.setVisible(self.history_visible)

    def _on_history_entry_clicked(self, url: QUrl) -> None:
        """Restore a clicked history expression to the input field."""
        from urllib.parse import unquote
        url_str = url.toString()
        if url_str.startswith("expr:"):
            expr = unquote(url_str[5:])
            self.input_field.setText(expr)
            self.input_field.setFocus()
            result = self.evaluator.evaluate(expr)
            self._update_result_display(result)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.language_changed.connect(self._refresh_ui_for_language)
        dialog.exec()
        saved_theme = SettingsManager.get().settings.get("theme", "dark")
        if saved_theme != self.current_theme:
            self._apply_theme(saved_theme)

    def _refresh_ui_for_language(self) -> None:
        """Refresh UI elements when language changes."""
        translator = get_translator()
        self.setWindowTitle(translator("window_title_macos"))
        self._build_menu_bar()
        self.clear_btn.setText(t("action_clear_history"))
        self._render_history()

    def _show_help(self) -> None:
        """Show a help dialog listing available functions and variables."""
        translator = get_translator()
        func_list = sorted(
            [k for k in ExpressionEvaluator.SAFE_FUNCTIONS.keys() if not k.startswith("__")]
        )
        vars_list = sorted(ExpressionEvaluator.USER_VARS.keys())
        msg = translator("help_available_functions") + "\n" + ", ".join(func_list)
        if vars_list:
            msg += "\n\n" + translator("help_user_variables") + "\n" + ", ".join(vars_list)
        msg += "\n\n" + translator("help_formatting") + " " + SettingsManager.get().settings.get("thousands_separator", " ") + " " + translator("help_thousands_label") + ", " + SettingsManager.get().settings.get("decimal_separator", ".") + " " + translator("help_decimal_label")
        QMessageBox.information(self, translator("help_title"), msg)

    def export_history_to_path(self, file_path: str, fmt: str = "json") -> bool:
        """Export history to given file path in json or csv format.

        Returns True on success.
        """
        try:
            lines = [l for l in self._history_entries if l.strip()]

            if fmt == "json":
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({"entries": lines}, f, indent=2)
            else:
                # csv
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["expression", "result"])
                    for line in lines:
                        if " = " in line:
                            expr, res = line.split(" = ", 1)
                        else:
                            expr, res = line, ""
                        writer.writerow([expr, res])
            return True
        except Exception as e:
            logger.error("Failed to export history: %s", e)
            return False

    def _export_history_dialog(self) -> None:
        """Show a file dialog to export history."""
        translator = get_translator()
        fname, _ = QFileDialog.getSaveFileName(
            self,
            translator("export_title"),
            str(Path.home() / "keisanbako_history"),
            "JSON Files (*.json);;CSV Files (*.csv)",
        )
        if fname:
            fmt = "json" if fname.endswith(".json") else "csv"
            ok = self.export_history_to_path(fname, fmt)
            if ok:
                QMessageBox.information(self, translator("export_title"), translator("export_success"))
            else:
                QMessageBox.warning(self, translator("export_title"), translator("export_failed"))

    def _format_expression(self, expression: str) -> str:
        """Format an expression by adding spaces around operators."""
        formatted = expression

        # Add spaces around operators: +, -, *, /, **
        operators = [
            (r"(?<![*\s])\*(?!\*)", " * "),  # Single *
            (r"\*\*(?!\*)", " ** "),  # **
            (r"(?<!\+)\+(?!\+)", " + "),  # Single +
            (r"(?<![=!><])-(?![=>\s])", " - "),  # -
            (r"(?<![<>!=])/(?![=>\s])", " / "),  # /
        ]

        for pattern, replacement in operators:
            formatted = re.sub(pattern, replacement, formatted)

        # Clean up multiple spaces
        formatted = re.sub(r"  +", " ", formatted)

        # Strip leading/trailing spaces
        formatted = formatted.strip()

        return formatted

    def _on_text_changed(self, text: str) -> None:
        """Handle text change in input field with debouncing."""
        # If the user edits text, abandon any active history navigation state
        self._history_index = None
        self._history_temp_buffer = None

        # Store the text and restart the debounce timer
        self._deferred_text = text
        self._eval_timer.stop()
        self._eval_timer.start(DEBOUNCE_DELAY_MS)

    def _evaluate_deferred(self) -> None:
        """Evaluate the deferred expression after debounce timeout."""
        text = self._deferred_text

        # Update result in real-time
        result = self.evaluator.evaluate(text)
        self._update_result_display(result)

    def _update_result_display(self, result: CalculationResult) -> None:
        """Update the result label display."""
        self.result_label.setToolTip("")
        self.statusBar().clearMessage()

        if not result.value:
            self.result_label.setText("= ")
            apply_result_label_style(self.result_label, self.current_theme)
        elif result.is_error:
            error_text = result.error_message if result.error_message else result.value
            if result.error_type:
                self.result_label.setToolTip(error_text)
            self.result_label.setText(f"= {error_text}")
            apply_result_label_style_error(self.result_label, self.current_theme)
        else:
            if result.is_cached:
                self.statusBar().showMessage(t("status_cached"))
            self.result_label.setText(f"= {result.value}")
            apply_result_label_style(self.result_label, self.current_theme)

    def _on_enter_pressed(self) -> None:
        """Handle Enter key press to commit calculation."""
        expr = self.input_field.text().strip()

        if not expr or ExpressionEvaluator._is_comment(expr):
            return

        result = self.evaluator.evaluate(expr)

        # Format the expression for display
        formatted_expr = self._format_expression(expr)

        # Add to internal history entries and render
        # Use error_message for errors, value for success, and mark errors with prefix
        if result.is_error and result.error_message:
            display_value = f"⚠️ {result.error_message}"
        else:
            display_value = result.value
        new_entry = f"{formatted_expr} = {display_value}"
        self._history_entries.append(new_entry)
        # Re-render history with colors
        self._render_history()
        # Reset navigation state after committing
        self._history_index = None
        self._history_temp_buffer = None

        # Save history to file
        self._save_history()

        # Update `ans` so the next expression can reference the last result
        if not result.is_error and result.raw_value is not None:
            ExpressionEvaluator.USER_VARS["ans"] = result.raw_value

        # Always clear the input after committing; on error also clear the result label
        self.input_field.clear()
        if result.is_error:
            self.result_label.setText("= ")

        # Scroll to bottom
        scrollbar = self.history_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _save_history(self) -> None:
        """Save calculation history to file."""
        try:
            data = {"entries": self._history_entries}
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error("Failed to save history: %s", e)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts not covered by menu QActions."""
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C: Clear input (non-standard; Ctrl+T/H/E are handled by menu QActions)
            self.input_field.clear()
            self.result_label.setText("= ")
            self.result_label.setToolTip("")
            self.statusBar().clearMessage()
            event.accept()
        elif event.key() == Qt.Key.Key_C and event.modifiers() == (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            # Ctrl+Shift+C: Copy result to clipboard
            result_text = self.result_label.text()
            if result_text and result_text != "= ":
                clipboard_text = result_text.replace("= ", "", 1)
                app = QApplication.instance()
                if app:
                    app.clipboard().setText(clipboard_text)
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        """Intercept key events on input field to support history navigation, and resize events for history browser."""
        if obj is self.input_field and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Up:
                self._history_prev()
                return True
            if key == Qt.Key.Key_Down:
                self._history_next()
                return True
        elif obj == self.history_browser and event.type() == QEvent.Type.Resize:
            self._reposition_clear_button()
        return super().eventFilter(obj, event)

    def _history_prev(self) -> None:
        """Navigate to previous entry in input history (Up arrow)."""
        if not self._history_list:
            return

        # First time pressing Up: save current buffer
        if self._history_index is None:
            self._history_temp_buffer = self.input_field.text()
            self._history_index = len(self._history_list) - 1
        else:
            if self._history_index > 0:
                self._history_index -= 1

        self.input_field.setText(self._history_list[self._history_index])
        self.input_field.setCursorPosition(len(self.input_field.text()))

        # Update result display for the current history entry
        result = self.evaluator.evaluate(self._history_list[self._history_index])
        self._update_result_display(result)

    def _render_history(self) -> None:
        """Render the history entries into the history browser as HTML with colored results."""
        has_entries = bool(self._history_entries)
        self.clear_btn.setVisible(has_entries)

        # Show the help/examples block only when history is empty (empty-state UX)
        if has_entries:
            header_html = ""
        else:
            header_html = (
                f"<div style='font-family:{FONT_NAME}; font-size:{FONT_SIZE_HISTORY}px;'>"
                f"<div><b>{t('help_calculator_title')}</b></div>"
                f"<div style='font-size:smaller; color:gray;'>{t('help_instructions')}</div>"
                f"<div style='margin-bottom:8px; font-size:smaller; color:gray;'>"
                f"<b>{t('help_examples_title')}</b>"
                f"<ul style='margin:4px 0 0 18px; padding:0; color:gray; font-size:smaller;'>"
                f"<li>{t('help_example_arithmetic')}</li>"
                f"<li>{t('help_example_currency')}</li>"
                f"<li>{t('help_example_units')}</li>"
                f"<li>{t('help_example_date')}</li>"
                f"<li>{t('help_example_variables')}</li>"
                f"</ul>"
                f"</div>"
                f"</div>"
            )

        full_html = generate_history_html(self._history_entries, self.current_theme, header_html)
        self.history_browser.setHtml(full_html)

    def _history_next(self) -> None:
        """Navigate to next entry in input history (Down arrow)."""
        if not self._history_list or self._history_index is None:
            return

        if self._history_index < len(self._history_list) - 1:
            self._history_index += 1
            self.input_field.setText(self._history_list[self._history_index])
            # Update result display for the current history entry
            result = self.evaluator.evaluate(self._history_list[self._history_index])
            self._update_result_display(result)
        else:
            # Move past the last entry: show empty input box
            self._history_index = None
            self._history_temp_buffer = None
            self.input_field.setText("")
            self.result_label.setText("= ")

        self.input_field.setCursorPosition(len(self.input_field.text()))

    def _scroll_history_to_bottom(self) -> None:
        """Scroll the history browser to the bottom (safe to call anytime)."""
        try:
            scrollbar = self.history_browser.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception:
            # Non-fatal; ignore in headless/test environments
            pass

    def _clear_history(self, confirm: bool = True) -> None:
        """Clear history entries (optionally ask for confirmation)."""
        if confirm:
            reply = QMessageBox.question(
                self,
                t("confirm_clear_title"),
                t("confirm_clear_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Clear internal structures and re-render/save
        self._history_entries = []
        self._render_history()
        self._save_history()

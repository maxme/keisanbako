"""Configuration constants for the Keisanbako calculator.

This module centralizes all magic numbers, timeouts, paths, and UI configuration
to make the codebase more maintainable and easier to tweak.
"""

from pathlib import Path
from typing import Dict

# ============================================================================
# UI Window Configuration
# ============================================================================

WINDOW_WIDTH: int = 700
WINDOW_HEIGHT: int = 500

# ============================================================================
# Font Configuration
# ============================================================================

FONT_NAME: str = "Menlo"
FONT_FAMILIES: list[str] = ["Menlo", "Consolas", "Courier New"]
FONT_SIZE_HISTORY: int = 13
FONT_SIZE_INPUT: int = 14
FONT_SIZE_RESULT: int = 14

# ============================================================================
# Timing Configuration (milliseconds)
# ============================================================================

# Debounce delay for input field evaluation to prevent excessive API calls
DEBOUNCE_DELAY_MS: int = 300

# Request cache TTL (time-to-live) in seconds
REQUEST_CACHE_TTL_SECONDS: float = 5.0

# API timeout in seconds
API_TIMEOUT_SECONDS: int = 2

# Delay for deferred theme application on startup (ms)
THEME_APPLY_DELAY_MS: int = 50

# Delay for deferred icon loading (ms)
ICON_LOAD_DELAY_MS: int = 100

# ============================================================================
# File Paths
# ============================================================================

HISTORY_FILE: Path = Path.home() / ".keisanbako_history.json"
SETTINGS_FILE: Path = Path.home() / ".keisanbako_settings.json"
CURRENCY_CACHE_FILE: Path = Path.home() / ".keisanbako_currency_cache.json"

# ============================================================================
# Dark Theme Colors
# ============================================================================

COLORS_DARK: Dict[str, str] = {
    "background_dark": "#1e1e1e",
    "background_input": "#252526",
    "text": "#d4d4d4",
    "text_white": "#ffffff",
    "border": "#333333",
    "border_input": "#3c3c3c",
    "success": "#7a9e7a",  # Desaturated green
    "error": "#a86666",  # Desaturated red
}

# ============================================================================
# Light Theme Colors
# ============================================================================

COLORS_LIGHT: Dict[str, str] = {
    "background_light": "#ffffff",
    "background_input_light": "#f3f3f3",
    "text_light": "#222222",
    "border_light": "#dddddd",
    "success_light": "#2e7d32",
    "error_light": "#b00020",
}

# ============================================================================
# Button Configuration
# ============================================================================

CLEAR_BUTTON_WIDTH: int = 82
CLEAR_BUTTON_MARGIN_RIGHT: int = 33  # Scrollbar margin
INPUT_FIELD_MIN_HEIGHT: int = 36
RESULT_LABEL_MIN_HEIGHT: int = 24

# ============================================================================
# History Formatting
# ============================================================================

HISTORY_MARGIN_BOTTOM: int = 4
HISTORY_ENTRY_MARGIN: int = 8

"""Settings management and formatting utilities for the calculator.

This module handles:
- Application-wide settings persistence
- Number and date formatting
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SettingsManager:
    """Persist application-wide settings for formatting and language."""

    SETTINGS_FILE: Path = Path.home() / ".keisanbako_settings.json"
    DEFAULTS = {
        "thousands_separator": " ",
        "decimal_separator": ".",
        "language": "en",
        "theme": "dark",
        "date_time_format": "iso",
    }
    _instance: Optional["SettingsManager"] = None

    def __init__(self) -> None:
        self.settings = self.DEFAULTS.copy()
        self.load()

    @classmethod
    def get(cls) -> "SettingsManager":
        """Get or create the singleton SettingsManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        """Load settings from file."""
        try:
            if not self.SETTINGS_FILE.exists():
                return
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.settings.update(self.DEFAULTS)
                self.settings.update(data)
        except Exception as e:
            logger.warning(f"Failed to load settings: {e}")
            self.settings = self.DEFAULTS.copy()

    def save(self) -> None:
        """Save settings to file."""
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save settings: {e}")

    def update(self, changes: dict) -> None:
        """Update settings and save.

        Args:
            changes: Dictionary of settings to update.
        """
        self.settings.update(changes)
        self.save()

    def copy(self) -> dict:
        """Get a copy of all settings.

        Returns:
            Dictionary of current settings.
        """
        return self.settings.copy()

    def get_value(self, key: str, default=None):
        """Get a specific setting value.

        Args:
            key: Setting key.
            default: Default value if key not found.

        Returns:
            Setting value or default.
        """
        return self.settings.get(key, default)


# ============================================================================
# Number Formatting
# ============================================================================


def format_number(val: int | float) -> str:
    """Format a number using the active user formatting settings.

    Args:
        val: The number to format.

    Returns:
        Formatted number string.
    """
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return str(val)

    settings = SettingsManager.get().settings
    thousands_sep = settings.get("thousands_separator", " ")
    decimal_sep = settings.get("decimal_separator", ".")

    if isinstance(val, float) and val.is_integer():
        val = int(val)

    negative = False
    if val < 0:
        negative = True
        val = -val

    val_str = str(val)
    parts = val_str.split(".")
    integer_part = parts[0]

    if thousands_sep:
        formatted_int = ""
        for i, char in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = thousands_sep + formatted_int
            formatted_int = char + formatted_int
    else:
        formatted_int = integer_part

    if len(parts) > 1:
        result = f"{formatted_int}{decimal_sep}{parts[1]}"
    else:
        result = formatted_int

    if negative:
        result = "-" + result
    return result


# ============================================================================
# Date Formatting
# ============================================================================


def format_date(d: date) -> str:
    """Format a date using the active user formatting preference.

    Args:
        d: The date to format.

    Returns:
        Formatted date string.
    """
    from datetime import datetime

    settings = SettingsManager.get().settings
    date_format = settings.get("date_time_format", "iso")

    if date_format == "iso":
        return d.isoformat()  # 2026-09-08
    elif date_format == "us":
        return d.strftime("%m/%d/%Y")  # 09/08/2026
    elif date_format == "eu":
        return d.strftime("%d/%m/%Y")  # 08/09/2026
    elif date_format == "long":
        return d.strftime("%B %d, %Y")  # September 08, 2026
    elif date_format == "abbr":
        return d.strftime("%b %d, %Y")  # Sep 08, 2026
    elif date_format == "iso_time":
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")  # 2026-09-08 14:30:45
    else:
        return d.isoformat()

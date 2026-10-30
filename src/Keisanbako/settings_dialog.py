"""Settings dialog for the Keisanbako calculator."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
)

from .settings import SettingsManager
from .translations import get_translator, set_language


class SettingsDialog(QDialog):
    """Simple settings page for display preferences."""

    # Signal emitted when language is changed
    language_changed = Signal()

    def __init__(self, parent: Optional[object] = None) -> None:
        """Initialize the settings dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        translator = get_translator()
        self.setWindowTitle(translator("settings_title"))
        self.resize(360, 280)

        self.settings = SettingsManager.get().settings.copy()
        form = QFormLayout(self)

        self.thousands_combo: QComboBox = QComboBox()
        self.thousands_combo.addItem(translator("thousands_space"), " ")
        self.thousands_combo.addItem(translator("thousands_comma"), ",")
        self.thousands_combo.addItem(translator("thousands_dot"), ".")
        self.thousands_combo.addItem(translator("thousands_none"), "")
        current_thousands = self.settings.get("thousands_separator", " ")
        if current_thousands in [" ", ",", ".", ""]:
            self.thousands_combo.setCurrentIndex([" ", ",", ".", ""].index(current_thousands))
        else:
            self.thousands_combo.setCurrentIndex(0)
        form.addRow(translator("settings_thousands_separator"), self.thousands_combo)

        self.decimal_combo: QComboBox = QComboBox()
        self.decimal_combo.addItem(translator("decimal_dot"), ".")
        self.decimal_combo.addItem(translator("decimal_comma"), ",")
        current_decimal = self.settings.get("decimal_separator", ".")
        self.decimal_combo.setCurrentIndex(0 if current_decimal == "." else 1)
        form.addRow(translator("settings_decimal_separator"), self.decimal_combo)

        self.language_combo: QComboBox = QComboBox()
        translator_manager = get_translator()
        language_index = 0
        for idx, lang_code in enumerate(translator_manager.SUPPORTED_LANGUAGES):
            lang_name = translator_manager.LANGUAGE_NAMES.get(lang_code, lang_code)
            self.language_combo.addItem(lang_name, lang_code)
            if lang_code == self.settings.get("language", "en"):
                language_index = idx
        self.language_combo.setCurrentIndex(language_index)
        form.addRow(translator("settings_language"), self.language_combo)

        self.theme_combo: QComboBox = QComboBox()
        self.theme_combo.addItem(translator("theme_dark"), "dark")
        self.theme_combo.addItem(translator("theme_light"), "light")
        current_theme = self.settings.get("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        form.addRow(translator("settings_theme"), self.theme_combo)

        self.date_time_combo: QComboBox = QComboBox()
        self.date_time_combo.addItem(translator("date_format_iso"), "iso")
        self.date_time_combo.addItem(translator("date_format_us"), "us")
        self.date_time_combo.addItem(translator("date_format_eu"), "eu")
        self.date_time_combo.addItem(translator("date_format_long"), "long")
        self.date_time_combo.addItem(translator("date_format_abbr"), "abbr")
        self.date_time_combo.addItem(translator("date_format_iso_time"), "iso_time")
        current_date_format = self.settings.get("date_time_format", "iso")
        format_index = {"iso": 0, "us": 1, "eu": 2, "long": 3, "abbr": 4, "iso_time": 5}.get(current_date_format, 0)
        self.date_time_combo.setCurrentIndex(format_index)
        form.addRow(translator("settings_date_time_format"), self.date_time_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self) -> None:
        """Accept settings changes and save them."""
        old_language = self.settings.get("language", "en")
        settings = {
            "thousands_separator": self.thousands_combo.currentData(),
            "decimal_separator": self.decimal_combo.currentData(),
            "language": self.language_combo.currentData(),
            "theme": self.theme_combo.currentData(),
            "date_time_format": self.date_time_combo.currentData(),
        }
        SettingsManager.get().update(settings)
        # Apply language change immediately
        set_language(settings["language"])
        # Emit signal if language changed
        if old_language != settings["language"]:
            self.language_changed.emit()
        super().accept()

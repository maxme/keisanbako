"""Translation management system for Keisanbako calculator.

This module provides a centralized translation system supporting multiple languages.
Translations are loaded from JSON files and cached for performance.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TranslationManager:
    """Manages translations for the calculator application."""

    # Default language
    DEFAULT_LANGUAGE = "en"

    # Supported languages
    SUPPORTED_LANGUAGES = ["en", "fr", "es", "zh_Hans", "zh_Hant", "ja"]

    # Language display names
    LANGUAGE_NAMES = {
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "zh_Hans": "简体中文",
        "zh_Hant": "繁體中文",
        "ja": "日本語",
    }

    def __init__(self) -> None:
        """Initialize the translation manager."""
        self._translations: Dict[str, Dict[str, str]] = {}
        self._current_language: str = self.DEFAULT_LANGUAGE
        
        # Determine the path to translations based on how the app is running
        base_path = None
        
        # Strategy 1: Try to use __path__ from the Keisanbako package (works in Nuitka)
        try:
            import Keisanbako
            if hasattr(Keisanbako, '__path__'):
                pkg_path = Path(Keisanbako.__path__[0])
                trans_path = pkg_path / "translations"
                if trans_path.exists():
                    base_path = trans_path
                    logger.debug(f"Using Keisanbako package path: {base_path}")
        except:
            pass
        
        # Strategy 2: Try relative to __file__ (works in source)
        if base_path is None:
            try:
                module_path = Path(__file__).parent
                if (module_path / "translations").exists():
                    base_path = module_path / "translations"
                    logger.debug(f"Using __file__ relative path: {base_path}")
            except:
                pass
        
        # Strategy 3: For PyInstaller bundles (check sys._MEIPASS)
        if base_path is None and hasattr(sys, '_MEIPASS'):
            meipass_path = Path(sys._MEIPASS) / "Keisanbako" / "translations"
            if meipass_path.exists():
                base_path = meipass_path
                logger.debug(f"Using PyInstaller bundle path: {base_path}")
        
        # Fallback: assume it's next to this file
        if base_path is None:
            base_path = Path(__file__).parent / "translations"
        
        self._translations_dir = base_path
        logger.debug(f"Final translations directory: {self._translations_dir}")

        # Lazy load translations: only load current language + English fallback on startup
        self._load_language(self.DEFAULT_LANGUAGE)

    def _load_language(self, language: str) -> None:
        """Load a specific language translation file."""
        if language in self._translations:
            return  # Already loaded
        
        if not self._translations_dir.exists():
            logger.warning(f"Translations directory not found: {self._translations_dir}")
            if language not in self._translations:
                self._translations[language] = self._get_default_translations()
            return

        translation_file = self._translations_dir / f"{language}.json"
        if translation_file.exists():
            try:
                with open(translation_file, "r", encoding="utf-8") as f:
                    self._translations[language] = json.load(f)
                    logger.debug(f"Loaded translations for language: {language}")
            except Exception as e:
                logger.error(f"Failed to load translations for {language}: {e}")
                self._translations[language] = self._get_default_translations()
        else:
            logger.debug(f"Translation file not found: {translation_file}")
            self._translations[language] = self._get_default_translations()

    def _load_all_translations(self) -> None:
        """Load all translation files from the translations directory (used on-demand)."""
        for lang in self.SUPPORTED_LANGUAGES:
            if lang not in self._translations:
                self._load_language(lang)

    @staticmethod
    def _get_default_translations() -> Dict[str, str]:
        """Get default (English) translations as fallback."""
        return {
            # Menu items
            "menu_file": "File",
            "menu_settings": "Settings",
            "menu_help": "Help",

            # File menu actions
            "action_export_history": "Export History",
            "action_clear_history": "Clear History",
            "action_exit": "Exit",

            # Settings menu actions
            "action_settings": "Open Settings",

            # Help menu actions
            "action_help": "Show Help",

            # Settings Dialog
            "settings_title": "Settings",
            "settings_thousands_separator": "Thousands separator",
            "settings_decimal_separator": "Decimal separator",
            "settings_language": "Language",
            "settings_date_time_format": "Date & Time Format",

            # Thousands separator options
            "thousands_space": "Space (1 234)",
            "thousands_comma": "Comma (1,234)",
            "thousands_dot": "Dot (1.234)",
            "thousands_none": "None (1234)",

            # Decimal separator options
            "decimal_dot": "Dot (.)",
            "decimal_comma": "Comma (,)",

            # Date/Time format options
            "date_format_iso": "ISO (2026-09-08)",
            "date_format_us": "US (09/08/2026)",
            "date_format_eu": "EU (08/09/2026)",
            "date_format_long": "Long (September 08, 2026)",
            "date_format_abbr": "Abbreviated (Sep 08, 2026)",
            "date_format_iso_time": "ISO with Time (2026-09-08 14:30:45)",

            # Dialog buttons
            "button_ok": "OK",
            "button_cancel": "Cancel",

            # Main Window
            "window_title_macos": "Keisanbako (macOS)",
            "input_placeholder": "Enter expression...",

            # Help dialog
            "help_title": "Keisanbako Help",
            "help_available_functions": "Available functions:",
            "help_user_variables": "User variables:",
            "help_formatting": "Formatting:",
            "help_thousands_label": "thousands",
            "help_decimal_label": "decimal",

            # Export dialog
            "export_title": "Export",
            "export_success": "History exported successfully",
            "export_failed": "Failed to export history",

            # Messages
            "message_no_calculation": "Please enter an expression",
        }

    def set_language(self, language: str) -> bool:
        """Set the current language.

        Args:
            language: Language code (e.g., 'en', 'fr', 'es').

        Returns:
            True if language was successfully set, False otherwise.
        """
        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {language}")
            return False
        
        # Lazy load the language if not already loaded
        self._load_language(language)
        
        self._current_language = language
        logger.debug(f"Language changed to: {language}")
        return True

    def get_language(self) -> str:
        """Get the current language code."""
        return self._current_language

    def translate(self, key: str, default: Optional[str] = None) -> str:
        """Translate a key using the current language.

        Args:
            key: Translation key.
            default: Default string if translation not found.

        Returns:
            Translated string or default if not found.
        """
        # Try current language
        if self._current_language in self._translations:
            translations = self._translations[self._current_language]
            if key in translations:
                return translations[key]

        # Fall back to English
        if "en" in self._translations:
            if key in self._translations["en"]:
                return self._translations["en"][key]

        # Use provided default or return the key itself
        return default or key

    def __call__(self, key: str, default: Optional[str] = None) -> str:
        """Allow the manager to be used as a callable function.

        This enables usage like: t("menu_file") instead of t.translate("menu_file")
        """
        return self.translate(key, default)


# Global translation manager instance
_translation_manager: Optional[TranslationManager] = None


def get_translator() -> TranslationManager:
    """Get or create the global translation manager.

    Returns:
        The global TranslationManager instance.
    """
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def t(key: str, default: Optional[str] = None) -> str:
    """Convenience function for translation.

    Args:
        key: Translation key.
        default: Default string if translation not found.

    Returns:
        Translated string.
    """
    return get_translator().translate(key, default)


def set_language(language: str) -> bool:
    """Set the global language.

    Args:
        language: Language code.

    Returns:
        True if successful.
    """
    return get_translator().set_language(language)


def get_language() -> str:
    """Get the current language code.

    Returns:
        Current language code.
    """
    return get_translator().get_language()

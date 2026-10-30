"""Tests for the translation system."""

import unittest
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from Keisanbako.translations import (
    TranslationManager,
    get_translator,
    t,
    set_language,
    get_language,
)


class TestTranslationManager(unittest.TestCase):
    """Tests for translation management."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = TranslationManager()
        # Ensure all translations are loaded for testing
        self.manager._load_all_translations()

    def test_default_language(self):
        """Test that default language is English."""
        self.assertEqual(self.manager.DEFAULT_LANGUAGE, "en")

    def test_supported_languages(self):
        """Test that all supported languages are listed."""
        self.assertIn("en", self.manager.SUPPORTED_LANGUAGES)
        self.assertIn("fr", self.manager.SUPPORTED_LANGUAGES)
        self.assertIn("es", self.manager.SUPPORTED_LANGUAGES)
        self.assertIn("zh_Hans", self.manager.SUPPORTED_LANGUAGES)
        self.assertIn("zh_Hant", self.manager.SUPPORTED_LANGUAGES)
        self.assertIn("ja", self.manager.SUPPORTED_LANGUAGES)

    def test_language_names(self):
        """Test language display names."""
        self.assertEqual(self.manager.LANGUAGE_NAMES["en"], "English")
        self.assertEqual(self.manager.LANGUAGE_NAMES["fr"], "Français")
        self.assertEqual(self.manager.LANGUAGE_NAMES["es"], "Español")
        self.assertEqual(self.manager.LANGUAGE_NAMES["zh_Hans"], "简体中文")
        self.assertEqual(self.manager.LANGUAGE_NAMES["zh_Hant"], "繁體中文")
        self.assertEqual(self.manager.LANGUAGE_NAMES["ja"], "日本語")

    def test_english_translations_loaded(self):
        """Test that English translations are loaded."""
        self.assertIn("en", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["en"])
        self.assertEqual(self.manager._translations["en"]["menu_file"], "File")

    def test_french_translations_loaded(self):
        """Test that French translations are loaded."""
        self.assertIn("fr", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["fr"])
        self.assertEqual(self.manager._translations["fr"]["menu_file"], "Fichier")

    def test_spanish_translations_loaded(self):
        """Test that Spanish translations are loaded."""
        self.assertIn("es", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["es"])
        self.assertEqual(self.manager._translations["es"]["menu_file"], "Archivo")

    def test_simplified_chinese_translations_loaded(self):
        """Test that Simplified Chinese translations are loaded."""
        self.assertIn("zh_Hans", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["zh_Hans"])
        self.assertEqual(self.manager._translations["zh_Hans"]["menu_file"], "文件")

    def test_traditional_chinese_translations_loaded(self):
        """Test that Traditional Chinese translations are loaded."""
        self.assertIn("zh_Hant", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["zh_Hant"])
        self.assertEqual(self.manager._translations["zh_Hant"]["menu_file"], "檔案")

    def test_japanese_translations_loaded(self):
        """Test that Japanese translations are loaded."""
        self.assertIn("ja", self.manager._translations)
        self.assertIn("menu_file", self.manager._translations["ja"])
        self.assertEqual(self.manager._translations["ja"]["menu_file"], "ファイル")

    def test_set_language_english(self):
        """Test setting language to English."""
        result = self.manager.set_language("en")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "en")

    def test_set_language_french(self):
        """Test setting language to French."""
        result = self.manager.set_language("fr")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "fr")

    def test_set_language_spanish(self):
        """Test setting language to Spanish."""
        result = self.manager.set_language("es")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "es")

    def test_set_language_simplified_chinese(self):
        """Test setting language to Simplified Chinese."""
        result = self.manager.set_language("zh_Hans")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "zh_Hans")

    def test_set_language_traditional_chinese(self):
        """Test setting language to Traditional Chinese."""
        result = self.manager.set_language("zh_Hant")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "zh_Hant")

    def test_set_language_japanese(self):
        """Test setting language to Japanese."""
        result = self.manager.set_language("ja")
        self.assertTrue(result)
        self.assertEqual(self.manager.get_language(), "ja")

    def test_set_invalid_language(self):
        """Test setting an invalid language."""
        result = self.manager.set_language("invalid")
        self.assertFalse(result)

    def test_translate_english(self):
        """Test translation to English."""
        self.manager.set_language("en")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "File")

    def test_translate_french(self):
        """Test translation to French."""
        self.manager.set_language("fr")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "Fichier")

    def test_translate_spanish(self):
        """Test translation to Spanish."""
        self.manager.set_language("es")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "Archivo")

    def test_translate_simplified_chinese(self):
        """Test translation to Simplified Chinese."""
        self.manager.set_language("zh_Hans")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "文件")

    def test_translate_traditional_chinese(self):
        """Test translation to Traditional Chinese."""
        self.manager.set_language("zh_Hant")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "檔案")

    def test_translate_japanese(self):
        """Test translation to Japanese."""
        self.manager.set_language("ja")
        result = self.manager.translate("menu_file")
        self.assertEqual(result, "ファイル")

    def test_translate_missing_key_fallback(self):
        """Test translation fallback for missing keys."""
        self.manager.set_language("en")
        result = self.manager.translate("nonexistent_key", "Default Value")
        self.assertEqual(result, "Default Value")

    def test_translate_callable(self):
        """Test using translation manager as a callable."""
        self.manager.set_language("en")
        result = self.manager("menu_file")
        self.assertEqual(result, "File")

    def test_all_keys_have_english_translation(self):
        """Test that all keys have at least English translations."""
        english_keys = set(self.manager._translations["en"].keys())
        for lang in ["fr", "es", "zh_Hans", "zh_Hant", "ja"]:
            lang_keys = set(self.manager._translations[lang].keys())
            missing = english_keys - lang_keys
            self.assertEqual(len(missing), 0, f"Missing keys in {lang}: {missing}")

    def test_settings_translations(self):
        """Test settings-related translations."""
        self.manager.set_language("en")
        self.assertEqual(self.manager("settings_title"), "Settings")
        self.assertEqual(
            self.manager("settings_thousands_separator"), "Thousands separator"
        )
        self.assertEqual(self.manager("settings_language"), "Language")

    def test_menu_translations(self):
        """Test menu translations."""
        self.manager.set_language("en")
        self.assertEqual(self.manager("menu_file"), "File")
        self.assertEqual(self.manager("menu_settings"), "Settings")
        self.assertEqual(self.manager("menu_help"), "Help")

    def test_action_translations(self):
        """Test action translations."""
        self.manager.set_language("en")
        self.assertEqual(self.manager("action_export_history"), "Export History")
        self.assertEqual(self.manager("action_clear_history"), "Clear")
        self.assertEqual(self.manager("action_exit"), "Exit")


class TestTranslationFunctions(unittest.TestCase):
    """Tests for translation convenience functions."""

    def test_get_translator(self):
        """Test getting the global translator instance."""
        manager = get_translator()
        self.assertIsNotNone(manager)
        self.assertIsInstance(manager, TranslationManager)

    def test_translate_function(self):
        """Test the convenience translate function."""
        set_language("en")
        result = t("menu_file")
        self.assertEqual(result, "File")

    def test_set_language_function(self):
        """Test the convenience set_language function."""
        result = set_language("fr")
        self.assertTrue(result)
        self.assertEqual(get_language(), "fr")

    def test_get_language_function(self):
        """Test the convenience get_language function."""
        set_language("es")
        result = get_language()
        self.assertEqual(result, "es")

    def test_language_persistence_across_calls(self):
        """Test that language setting persists across function calls."""
        set_language("fr")
        self.assertEqual(get_language(), "fr")
        self.assertEqual(t("menu_file"), "Fichier")


if __name__ == "__main__":
    unittest.main()

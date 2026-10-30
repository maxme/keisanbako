"""Theme management for the Keisanbako calculator UI.

Handles dark/light theme colors, styling, and theme switching.
"""

from typing import Literal, NamedTuple

from PySide6.QtWidgets import QTextBrowser, QLineEdit, QLabel

from .constants import COLORS_DARK, COLORS_LIGHT, FONT_NAME, FONT_SIZE_HISTORY


ThemeType = Literal["dark", "light"]


class ThemeColors(NamedTuple):
    background: str
    input_bg: str
    text: str
    border: str
    success: str
    error: str


def get_theme_colors(theme: ThemeType) -> ThemeColors:
    """Get theme colors for the given theme type."""
    if theme == "light":
        return ThemeColors(
            background=COLORS_LIGHT["background_light"],
            input_bg=COLORS_LIGHT["background_input_light"],
            text=COLORS_LIGHT["text_light"],
            border=COLORS_LIGHT["border_light"],
            success=COLORS_LIGHT["success_light"],
            error=COLORS_LIGHT["error_light"],
        )
    return ThemeColors(
        background=COLORS_DARK["background_dark"],
        input_bg=COLORS_DARK["background_input"],
        text=COLORS_DARK["text"],
        border=COLORS_DARK["border"],
        success=COLORS_DARK["success"],
        error=COLORS_DARK["error"],
    )


def apply_history_browser_style(
    browser: QTextBrowser, theme: ThemeType
) -> None:
    """Apply theme styling to history text browser."""
    colors = get_theme_colors(theme)
    browser.setStyleSheet(
        f"background-color: {colors.background}; "
        f"color: {colors.text}; "
        f"border-radius: 6px; "
        f"border: 1px solid {colors.border}; "
        f"padding: 10px;"
    )


def apply_input_field_style(
    field: QLineEdit, theme: ThemeType
) -> None:
    """Apply theme styling to input field."""
    colors = get_theme_colors(theme)
    field.setStyleSheet(
        f"background-color: {colors.input_bg}; "
        f"color: {colors.text}; "
        f"border: 1px solid {colors.border}; "
        f"border-radius: 6px; "
        f"padding: 8px;"
    )


def apply_result_label_style(
    label: QLabel, theme: ThemeType
) -> None:
    """Apply theme styling to result label."""
    colors = get_theme_colors(theme)
    label.setStyleSheet(f"color: {colors.success}; padding: 5px;")


def apply_result_label_style_error(
    label: QLabel, theme: ThemeType
) -> None:
    """Apply error styling to result label."""
    colors = get_theme_colors(theme)
    label.setStyleSheet(f"color: {colors.error}; padding: 5px;")


def get_clear_button_stylesheet(theme: ThemeType = "dark") -> str:
    """Get the stylesheet for the clear button."""
    if theme == "light":
        return (
            "QPushButton { background-color: #e0e0e0; color: #222222; border: 1px solid #aaaaaa; border-radius: 6px; padding: 6px 10px; }"
            "QPushButton:hover { background-color: #d0d0d0; }"
        )
    return (
        "QPushButton { background-color: #3a3a3a; color: #f0f0f0; border: 1px solid #555; border-radius: 6px; padding: 6px 10px; }"
        "QPushButton:hover { background-color: #4a4a4a; }"
    )


def get_status_bar_stylesheet(theme: ThemeType) -> str:
    """Get the stylesheet for the status bar."""
    colors = get_theme_colors(theme)
    return (
        f"QStatusBar {{ background-color: {colors.background}; color: {colors.text}; "
        f"border-top: 1px solid {colors.border}; font-size: 11px; padding: 2px 6px; }}"
    )


def generate_history_html(
    entries: list[str],
    theme: ThemeType,
    header_html: str,
) -> str:
    """Generate HTML for history display with theme colors."""
    import html as _html
    from urllib.parse import quote

    colors = get_theme_colors(theme)

    body_parts = [header_html]
    for entry in entries:
        expr = _html.escape(entry)
        # Split expression and result if present
        if " = " in entry:
            left, right = entry.split(" = ", 1)
            left_html = _html.escape(left)
            right_html = _html.escape(right)
            # Check if result is an error by looking for the error marker prefix
            is_error_result = right.strip().startswith("⚠️")
            col = colors.error if is_error_result else colors.success
            # Wrap expression in an anchor so clicking it restores it to the input
            href = "expr:" + quote(left, safe="")
            line_html = (
                f"<div style='font-family:{FONT_NAME}; font-size:{FONT_SIZE_HISTORY}px; margin-bottom:4px;'>"
                f"<a href='{href}' style='text-decoration:none; color:{colors.text};'>{left_html}</a> "
                f"= <span style='color:{col};'>{right_html}</span>"
                f"</div>"
            )
        else:
            line_html = (
                f"<div style='font-family:{FONT_NAME}; font-size:{FONT_SIZE_HISTORY}px; margin-bottom:4px; color:{colors.text};'>{expr}</div>"
            )
        body_parts.append(line_html)

    full_html = "<div>" + "".join(body_parts) + "</div>"
    return full_html

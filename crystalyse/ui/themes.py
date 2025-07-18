"""
Theme system for CrystaLyse.AI

Provides sophisticated theming capabilities inspired by gemini-cli.
"""

from typing import List
from dataclasses import dataclass
from enum import Enum
from rich.style import Style
from rich.theme import Theme as RichTheme


class ThemeType(Enum):
    """Theme types available."""
    LIGHT = "light"
    DARK = "dark"
    CRYSTALYSE_DARK = "crystalyse_dark"
    CRYSTALYSE_LIGHT = "crystalyse_light"
    CRYSTALYSE_RED = "crystalyse_red"
    HIGH_CONTRAST = "high_contrast"


@dataclass
class ColorScheme:
    """Color scheme for themes."""
    # Base colors
    background: str
    foreground: str

    # Accent colors
    accent_blue: str
    accent_purple: str
    accent_cyan: str
    accent_green: str
    accent_yellow: str
    accent_red: str
    accent_orange: str

    # UI colors
    border: str
    highlight: str
    dim: str
    comment: str

    # Gradient colors
    gradient_colors: List[str]

    # Status colors
    success: str
    error: str
    warning: str
    info: str


# Define color schemes
DARK_SCHEME = ColorScheme(
    background="#1e1e2e",
    foreground="#cdd6f4",
    accent_blue="#89b4fa",
    accent_purple="#cba6f7",
    accent_cyan="#89dceb",
    accent_green="#a6e3a1",
    accent_yellow="#f9e2af",
    accent_red="#f38ba8",
    accent_orange="#fab387",
    border="#6c7086",
    highlight="#585b70",
    dim="#6c7086",
    comment="#6c7086",
    gradient_colors=["#4796E4", "#847ACE", "#C3677F"],
    success="#a6e3a1",
    error="#f38ba8",
    warning="#f9e2af",
    info="#89b4fa"
)

LIGHT_SCHEME = ColorScheme(
    background="#fafafa",
    foreground="#3c3c43",
    accent_blue="#3b82f6",
    accent_purple="#8b5cf6",
    accent_cyan="#06b6d4",
    accent_green="#22c55e",
    accent_yellow="#d97706",
    accent_red="#dc2626",
    accent_orange="#ea580c",
    border="#e5e7eb",
    highlight="#f3f4f6",
    dim="#9ca3af",
    comment="#6b7280",
    gradient_colors=["#4796E4", "#847ACE", "#C3677F"],
    success="#22c55e",
    error="#dc2626",
    warning="#d97706",
    info="#3b82f6"
)

CRYSTALYSE_DARK_SCHEME = ColorScheme(
    background="#0f0f1a",
    foreground="#e2e8f0",
    accent_blue="#1e40af",
    accent_purple="#7c3aed",
    accent_cyan="#0891b2",
    accent_green="#059669",
    accent_yellow="#d97706",
    accent_red="#dc2626",
    accent_orange="#ea580c",
    border="#334155",
    highlight="#1e293b",
    dim="#64748b",
    comment="#64748b",
    gradient_colors=["#1e40af", "#7c3aed", "#0891b2"],
    success="#059669",
    error="#dc2626",
    warning="#d97706",
    info="#1e40af"
)

CRYSTALYSE_LIGHT_SCHEME = ColorScheme(
    background="#ffffff",
    foreground="#1e293b",
    accent_blue="#1e40af",
    accent_purple="#7c3aed",
    accent_cyan="#0891b2",
    accent_green="#059669",
    accent_yellow="#d97706",
    accent_red="#dc2626",
    accent_orange="#ea580c",
    border="#e2e8f0",
    highlight="#f1f5f9",
    dim="#64748b",
    comment="#94a3b8",
    gradient_colors=["#1e40af", "#7c3aed", "#0891b2"],
    success="#059669",
    error="#dc2626",
    warning="#d97706",
    info="#1e40af"
)

CRYSTALYSE_RED_SCHEME = ColorScheme(
    background="#1a0a0a",
    foreground="#ffcccc",
    accent_blue="#ff4444",
    accent_purple="#ff6666",
    accent_cyan="#ff8888",
    accent_green="#ffaaaa",
    accent_yellow="#ffcc44",
    accent_red="#ff0000",
    accent_orange="#ff6600",
    border="#cc4444",
    highlight="#330000",
    dim="#cc6666",
    comment="#cc6666",
    gradient_colors=["#ff0000", "#ff4444", "#ff6666", "#ff8888"],
    success="#ff6666",
    error="#ff0000",
    warning="#ffcc44",
    info="#ff4444"
)

HIGH_CONTRAST_SCHEME = ColorScheme(
    background="#000000",
    foreground="#ffffff",
    accent_blue="#0080ff",
    accent_purple="#ff00ff",
    accent_cyan="#00ffff",
    accent_green="#00ff00",
    accent_yellow="#ffff00",
    accent_red="#ff0000",
    accent_orange="#ff8000",
    border="#ffffff",
    highlight="#333333",
    dim="#888888",
    comment="#888888",
    gradient_colors=["#0080ff", "#ff00ff", "#00ffff"],
    success="#00ff00",
    error="#ff0000",
    warning="#ffff00",
    info="#0080ff"
)

# Theme registry
THEMES = {
    ThemeType.DARK: DARK_SCHEME,
    ThemeType.LIGHT: LIGHT_SCHEME,
    ThemeType.CRYSTALYSE_DARK: CRYSTALYSE_DARK_SCHEME,
    ThemeType.CRYSTALYSE_LIGHT: CRYSTALYSE_LIGHT_SCHEME,
    ThemeType.CRYSTALYSE_RED: CRYSTALYSE_RED_SCHEME,
    ThemeType.HIGH_CONTRAST: HIGH_CONTRAST_SCHEME
}


class CrystaLyseTheme:
    """CrystaLyse.AI theme with Rich integration."""

    def __init__(self, theme_type: ThemeType = ThemeType.CRYSTALYSE_DARK):
        self.theme_type = theme_type
        self.colors = THEMES[theme_type]
        self._rich_theme = self._create_rich_theme()

    def _create_rich_theme(self) -> RichTheme:
        """Create Rich theme from color scheme."""
        return RichTheme({
            # Base styles
            "base": Style(color=self.colors.foreground, bgcolor=self.colors.background),
            "dim": Style(color=self.colors.dim),
            "comment": Style(color=self.colors.comment),
            "border": Style(color=self.colors.border),
            "highlight": Style(bgcolor=self.colors.highlight),

            # Accent styles
            "accent.blue": Style(color=self.colors.accent_blue),
            "accent.purple": Style(color=self.colors.accent_purple),
            "accent.cyan": Style(color=self.colors.accent_cyan),
            "accent.green": Style(color=self.colors.accent_green),
            "accent.yellow": Style(color=self.colors.accent_yellow),
            "accent.red": Style(color=self.colors.accent_red),
            "accent.orange": Style(color=self.colors.accent_orange),

            # Status styles
            "status.success": Style(color=self.colors.success),
            "status.error": Style(color=self.colors.error),
            "status.warning": Style(color=self.colors.warning),
            "status.info": Style(color=self.colors.info),

            # UI component styles
            "header": Style(color=self.colors.accent_blue, bold=True),
            "title": Style(color=self.colors.foreground, bold=True),
            "subtitle": Style(color=self.colors.dim),
            "prompt": Style(color=self.colors.accent_cyan),
            "input": Style(color=self.colors.foreground),
            "output": Style(color=self.colors.foreground),
            "panel": Style(color=self.colors.foreground, bgcolor=self.colors.background),

            # Chat styles
            "chat.user": Style(color=self.colors.accent_blue, bold=True),
            "chat.assistant": Style(color=self.colors.accent_green, bold=True),
            "chat.system": Style(color=self.colors.accent_yellow),
            "chat.timestamp": Style(color=self.colors.dim),

            # Tool styles
            "tool.name": Style(color=self.colors.accent_purple, bold=True),
            "tool.success": Style(color=self.colors.success),
            "tool.error": Style(color=self.colors.error),
            "tool.warning": Style(color=self.colors.warning),

            # Material discovery styles
            "material.formula": Style(color=self.colors.accent_cyan, bold=True),
            "material.property": Style(color=self.colors.accent_purple),
            "material.value": Style(color=self.colors.accent_green),
            "material.unit": Style(color=self.colors.dim),

            # Progress styles
            "progress.bar": Style(color=self.colors.accent_blue),
            "progress.complete": Style(color=self.colors.success),
            "progress.failed": Style(color=self.colors.error),

            # Memory styles
            "memory.cached": Style(color=self.colors.accent_cyan),
            "memory.saved": Style(color=self.colors.success),
            "memory.context": Style(color=self.colors.dim),
        })

    @property
    def rich_theme(self) -> RichTheme:
        """Get the Rich theme object."""
        return self._rich_theme

    def get_gradient_colors(self) -> List[str]:
        """Get gradient colors for this theme."""
        return self.colors.gradient_colors

    def get_status_color(self, status: str) -> str:
        """Get color for status type."""
        status_map = {
            'success': self.colors.success,
            'error': self.colors.error,
            'warning': self.colors.warning,
            'info': self.colors.info
        }
        return status_map.get(status, self.colors.foreground)


class ThemeManager:
    """Manages theme switching and persistence."""

    def __init__(self, default_theme: ThemeType = ThemeType.CRYSTALYSE_RED):
        self._current_theme = CrystaLyseTheme(default_theme)
        self._theme_type = default_theme

    @property
    def current_theme(self) -> CrystaLyseTheme:
        """Get current theme."""
        return self._current_theme

    @property
    def theme_type(self) -> ThemeType:
        """Get current theme type."""
        return self._theme_type

    def set_theme(self, theme_type: ThemeType):
        """Set the current theme."""
        self._theme_type = theme_type
        self._current_theme = CrystaLyseTheme(theme_type)

    def get_available_themes(self) -> List[ThemeType]:
        """Get list of available themes."""
        return list(ThemeType)

    def get_theme_description(self, theme_type: ThemeType) -> str:
        """Get description of a theme."""
        descriptions = {
            ThemeType.DARK: "Dark theme with pleasant colors",
            ThemeType.LIGHT: "Light theme for bright environments",
            ThemeType.CRYSTALYSE_DARK: "CrystaLyse.AI branded dark theme",
            ThemeType.CRYSTALYSE_LIGHT: "CrystaLyse.AI branded light theme",
            ThemeType.CRYSTALYSE_RED: "CrystaLyse.AI red theme - stunning and bold",
            ThemeType.HIGH_CONTRAST: "High contrast theme for accessibility"
        }
        return descriptions.get(theme_type, "Unknown theme")


# Global theme manager instance
theme_manager = ThemeManager()

"""
CrystaLyse.AI Enhanced UI Components

This module provides sophisticated terminal UI components inspired by gemini-cli
but implemented using Rich for Python compatibility.
"""

from .themes import CrystaLyseTheme, ThemeManager
from .components import (
    CrystaLyseHeader,
    ChatDisplay,
    StatusBar,
    InputPanel,
    ProgressIndicator
)
from .ascii_art import CRYSTALYSE_ASCII_ART, get_responsive_logo
from .gradients import create_gradient_text, GradientStyle

__all__ = [
    'CrystaLyseTheme',
    'ThemeManager',
    'CrystaLyseHeader',
    'ChatDisplay',
    'StatusBar',
    'InputPanel',
    'ProgressIndicator',
    'CRYSTALYSE_ASCII_ART',
    'get_responsive_logo',
    'create_gradient_text',
    'GradientStyle'
]

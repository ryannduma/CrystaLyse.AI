"""
Gradient text effects for CrystaLyse.AI

Provides gradient text rendering using Rich's styling capabilities.
"""

from typing import List, Optional
from rich.text import Text
from rich.color import Color
from rich.style import Style
from enum import Enum


class GradientStyle(Enum):
    """Predefined gradient styles for CrystaLyse.AI."""
    CRYSTALYSE_BLUE = "crystalyse_blue"
    CRYSTALYSE_PURPLE = "crystalyse_purple"
    CRYSTALYSE_CYAN = "crystalyse_cyan"
    CRYSTALYSE_RED = "crystalyse_red"
    CRYSTALYSE_RAINBOW = "crystalyse_rainbow"
    GEMINI_INSPIRED = "gemini_inspired"


# Gradient color definitions
GRADIENT_COLORS = {
    GradientStyle.CRYSTALYSE_BLUE: [
        "#1e40af",  # Deep blue
        "#3b82f6",  # Blue
        "#60a5fa",  # Light blue
        "#93c5fd",  # Very light blue
    ],
    GradientStyle.CRYSTALYSE_PURPLE: [
        "#7c3aed",  # Deep purple
        "#8b5cf6",  # Purple
        "#a78bfa",  # Light purple
        "#c4b5fd",  # Very light purple
    ],
    GradientStyle.CRYSTALYSE_CYAN: [
        "#0891b2",  # Deep cyan
        "#0ea5e9",  # Cyan
        "#38bdf8",  # Light cyan
        "#7dd3fc",  # Very light cyan
    ],
    GradientStyle.CRYSTALYSE_RED: [
        "#cc0000",  # Deep red
        "#ff0000",  # Bright red
        "#ff4444",  # Light red
        "#ff6666",  # Very light red
    ],
    GradientStyle.CRYSTALYSE_RAINBOW: [
        "#ef4444",  # Red
        "#f97316",  # Orange
        "#eab308",  # Yellow
        "#22c55e",  # Green
        "#3b82f6",  # Blue
        "#8b5cf6",  # Purple
    ],
    GradientStyle.GEMINI_INSPIRED: [
        "#4796E4",  # Gemini blue
        "#847ACE",  # Gemini purple
        "#C3677F",  # Gemini pink
    ]
}


def interpolate_color(color1: str, color2: str, ratio: float) -> str:
    """
    Interpolate between two hex colors.
    
    Args:
        color1: Start color in hex format
        color2: End color in hex format
        ratio: Interpolation ratio (0.0 to 1.0)
        
    Returns:
        Interpolated color in hex format
    """
    # Parse hex colors
    c1 = Color.parse(color1)
    c2 = Color.parse(color2)

    # Convert to RGB
    r1, g1, b1 = c1.get_truecolor()
    r2, g2, b2 = c2.get_truecolor()

    # Interpolate
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)

    return f"#{r:02x}{g:02x}{b:02x}"


def create_gradient_text(
    text: str,
    gradient_style: GradientStyle = GradientStyle.CRYSTALYSE_BLUE,
    custom_colors: Optional[List[str]] = None
) -> Text:
    """
    Create gradient text using Rich's Text object.
    
    Args:
        text: Text to apply gradient to
        gradient_style: Predefined gradient style
        custom_colors: Optional custom color list
        
    Returns:
        Rich Text object with gradient applied
    """
    if custom_colors:
        colors = custom_colors
    else:
        colors = GRADIENT_COLORS[gradient_style]

    if not colors:
        return Text(text)

    # Handle single color
    if len(colors) == 1:
        return Text(text, style=Style(color=colors[0]))

    # Create gradient
    result = Text()
    text_length = len(text)

    if text_length <= 1:
        result.append(text, style=Style(color=colors[0]))
        return result

    # Calculate color for each character
    for i, char in enumerate(text):
        if char.isspace():
            result.append(char)
            continue

        # Calculate position along gradient (0.0 to 1.0)
        position = i / (text_length - 1)

        # Find which color segment we're in
        segment_size = 1.0 / (len(colors) - 1)
        segment_index = int(position / segment_size)

        # Handle edge case
        if segment_index >= len(colors) - 1:
            segment_index = len(colors) - 2

        # Calculate position within segment
        segment_position = (position - segment_index * segment_size) / segment_size

        # Interpolate color
        color = interpolate_color(colors[segment_index], colors[segment_index + 1], segment_position)
        result.append(char, style=Style(color=color))

    return result


def create_multiline_gradient_text(
    text: str,
    gradient_style: GradientStyle = GradientStyle.CRYSTALYSE_BLUE,
    custom_colors: Optional[List[str]] = None
) -> Text:
    """
    Create gradient text for multiline strings (like ASCII art).
    
    Args:
        text: Multiline text to apply gradient to
        gradient_style: Predefined gradient style
        custom_colors: Optional custom color list
        
    Returns:
        Rich Text object with gradient applied
    """
    if custom_colors:
        colors = custom_colors
    else:
        colors = GRADIENT_COLORS[gradient_style]

    if not colors:
        return Text(text)

    # For multiline text, use a single color to avoid complexity
    # Use the first color in the gradient
    main_color = colors[0] if colors else "#3b82f6"

    return Text(text, style=Style(color=main_color))


def create_rainbow_text(text: str) -> Text:
    """
    Create rainbow gradient text.
    
    Args:
        text: Text to apply rainbow gradient to
        
    Returns:
        Rich Text object with rainbow gradient
    """
    return create_gradient_text(text, GradientStyle.CRYSTALYSE_RAINBOW)


def create_crystalyse_branded_text(text: str) -> Text:
    """
    Create text with CrystaLyse.AI brand colors.
    
    Args:
        text: Text to apply brand gradient to
        
    Returns:
        Rich Text object with CrystaLyse.AI brand gradient
    """
    return create_gradient_text(text, GradientStyle.CRYSTALYSE_BLUE)


def create_status_gradient(text: str, status: str) -> Text:
    """
    Create gradient text based on status.
    
    Args:
        text: Text to apply gradient to
        status: Status type ('success', 'error', 'warning', 'info')
        
    Returns:
        Rich Text object with status-appropriate gradient
    """
    status_colors = {
        'success': ["#22c55e", "#16a34a", "#15803d"],
        'error': ["#ef4444", "#dc2626", "#b91c1c"],
        'warning': ["#f59e0b", "#d97706", "#b45309"],
        'info': ["#3b82f6", "#2563eb", "#1d4ed8"]
    }

    colors = status_colors.get(status, GRADIENT_COLORS[GradientStyle.CRYSTALYSE_BLUE])
    return create_gradient_text(text, custom_colors=colors)

#!/usr/bin/env python3
"""
Test ASCII art functionality.
"""

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from crystalyse.ui.ascii_art import get_responsive_logo, get_logo_with_subtitle

def main():
    console = Console()

    console.print("🎨 ASCII Art Test Demo")
    console.print("=" * 50)

    # Test responsive logo
    terminal_width = console.size.width
    console.print(f"Terminal width: {terminal_width}")

    logo = get_responsive_logo(terminal_width)
    console.print(Panel(
        Align.center(logo),
        title="[bold]Responsive Logo[/bold]",
        border_style="blue"
    ))

    # Test with subtitle
    logo_with_subtitle, subtitle = get_logo_with_subtitle(terminal_width, "1.0.0")
    console.print(Panel(
        Align.center(f"{logo_with_subtitle}\n{subtitle}"),
        title="[bold]Logo with Subtitle[/bold]",
        border_style="cyan"
    ))

    # Test different widths
    test_widths = [40, 60, 80, 100, 120]

    for width in test_widths:
        test_logo = get_responsive_logo(width)
        console.print(f"\n📏 Width {width}:")
        console.print(Panel(
            Align.center(test_logo),
            title=f"[bold]Width: {width}[/bold]",
            border_style="green"
        ))

if __name__ == "__main__":
    main()

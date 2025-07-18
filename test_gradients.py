#!/usr/bin/env python3
"""
Test gradient functionality.
"""

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from crystalyse.ui.gradients import create_gradient_text, GradientStyle

def main():
    console = Console()

    console.print("🎨 Gradient Test Demo")
    console.print("=" * 50)

    # Test different gradient styles
    gradient_styles = [
        (GradientStyle.CRYSTALYSE_BLUE, "CrystaLyse Blue"),
        (GradientStyle.CRYSTALYSE_PURPLE, "CrystaLyse Purple"),
        (GradientStyle.CRYSTALYSE_CYAN, "CrystaLyse Cyan"),
        (GradientStyle.CRYSTALYSE_RAINBOW, "CrystaLyse Rainbow"),
        (GradientStyle.GEMINI_INSPIRED, "Gemini Inspired")
    ]

    for style, name in gradient_styles:
        try:
            gradient_text = create_gradient_text("CrystaLyse.AI Materials Discovery", style)
            console.print(Panel(
                Align.center(gradient_text),
                title=f"[bold]{name}[/bold]",
                border_style="blue"
            ))
        except Exception as e:
            console.print(f"Error with {name}: {e}")

    # Test with chemical formulas
    formulas = ["LiCoO₂", "CsSnI₃", "CaTiO₃", "BaTiO₃"]

    console.print("\n🧪 Chemical Formula Gradients:")
    for formula in formulas:
        try:
            gradient_formula = create_gradient_text(formula, GradientStyle.CRYSTALYSE_BLUE)
            console.print(Panel(
                Align.center(gradient_formula),
                title=f"[bold]Formula: {formula}[/bold]",
                border_style="cyan"
            ))
        except Exception as e:
            console.print(f"Error with formula {formula}: {e}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Demo showing integration of enhanced UI with existing CrystaLyse.AI CLI.
"""

import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.status import Status

from crystalyse.ui.ascii_art import get_responsive_logo
from crystalyse.ui.gradients import create_gradient_text, GradientStyle


def enhanced_header(console: Console, version: str = "1.0.0"):
    """Enhanced header with gradient ASCII art."""
    terminal_width = console.size.width
    logo = get_responsive_logo(terminal_width)

    # Create gradient title
    gradient_title = create_gradient_text("CrystaLyse.AI", GradientStyle.CRYSTALYSE_BLUE)

    # Create header content
    header_content = Text()
    header_content.append(logo, style="blue")
    header_content.append(f"\n\nv{version} - AI-Powered Materials Discovery", style="dim")

    return Panel(
        Align.center(header_content),
        title="[bold cyan]Materials Discovery Platform[/bold cyan]",
        border_style="blue",
        padding=(1, 2)
    )


def enhanced_chat_interface(console: Console):
    """Demo enhanced chat interface."""
    # User input
    user_panel = Panel(
        "➤ Find a high-temperature superconductor with transition temperature above 100K",
        title="[bold cyan]You[/bold cyan]",
        border_style="cyan",
        padding=(0, 1)
    )
    console.print(user_panel)

    # Show analysis progress
    with Status("[bold green]Analyzing quantum materials database...", console=console, spinner="dots"):
        time.sleep(3)

    # Assistant response
    response_text = (
        "🔬 Based on your query, I recommend exploring cuprate superconductors, "
        "particularly YBa₂Cu₃O₇₋ₓ (YBCO) which exhibits superconductivity at 92K. "
        "I'll also analyze iron-based superconductors like FeSe and SmFeAsO₁₋ₓFₓ "
        "which show promising high-temperature properties."
    )

    assistant_panel = Panel(
        response_text,
        title="[bold green]CrystaLyse.AI[/bold green]",
        border_style="green",
        padding=(0, 1)
    )
    console.print(assistant_panel)


def enhanced_material_display(console: Console):
    """Demo enhanced material results display."""
    materials = [
        {
            "formula": "YBa₂Cu₃O₇₋ₓ",
            "name": "Yttrium Barium Copper Oxide",
            "Tc": "92 K",
            "type": "Cuprate superconductor",
            "crystal_system": "Orthorhombic"
        },
        {
            "formula": "SmFeAsO₁₋ₓFₓ",
            "name": "Samarium Iron Arsenic Oxide Fluoride",
            "Tc": "55 K",
            "type": "Iron-based superconductor",
            "crystal_system": "Tetragonal"
        }
    ]

    for material in materials:
        # Create gradient formula
        gradient_formula = create_gradient_text(material["formula"], GradientStyle.CRYSTALYSE_BLUE)

        # Create material content
        content = Text()
        content.append(gradient_formula.plain, style=gradient_formula.style)
        content.append(f"\n{material['name']}\n\n", style="dim")
        content.append("Critical Temperature: ", style="yellow")
        content.append(f"{material['Tc']}\n", style="green bold")
        content.append("Type: ", style="yellow")
        content.append(f"{material['type']}\n", style="cyan")
        content.append("Crystal System: ", style="yellow")
        content.append(f"{material['crystal_system']}", style="purple")

        material_panel = Panel(
            content,
            title="[bold]Superconductor Discovery[/bold]",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(material_panel)


def enhanced_status_display(console: Console):
    """Demo enhanced status display."""
    status_text = Text()
    status_text.append("🚀 Status: ", style="bold")
    status_text.append("Analysis Complete", style="green bold")
    status_text.append(" | Model: ", style="dim")
    status_text.append("gpt-4", style="blue")
    status_text.append(" | Session: ", style="dim")
    status_text.append("superconductor_research", style="cyan")
    status_text.append(" | Discoveries: ", style="dim")
    status_text.append("2 materials", style="yellow")

    status_panel = Panel(
        status_text,
        title="System Status",
        border_style="dim",
        padding=(0, 1)
    )
    console.print(status_panel)


def main():
    """Run the integration demo."""
    console = Console()

    print("🎨 CrystaLyse.AI Enhanced UI Integration Demo")
    print("=" * 60)
    print("This demo shows how the enhanced UI components can be")
    print("integrated with the existing CrystaLyse.AI CLI.\n")

    # Clear screen and show enhanced header
    console.clear()
    header = enhanced_header(console, "1.0.0")
    console.print(header)

    # Show welcome message
    welcome_text = Text()
    welcome_text.append("Welcome to the enhanced ", style="dim")
    gradient_name = create_gradient_text("CrystaLyse.AI", GradientStyle.CRYSTALYSE_BLUE)
    welcome_text.append(gradient_name.plain, style=gradient_name.style)
    welcome_text.append(" materials discovery platform!", style="dim")

    welcome_panel = Panel(
        Align.center(welcome_text),
        title="[bold]Welcome[/bold]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(welcome_panel)

    # Demo chat interface
    console.print("\n" + "=" * 60)
    console.print("💬 Enhanced Chat Interface Demo")
    console.print("=" * 60)
    enhanced_chat_interface(console)

    # Demo material display
    console.print("\n" + "=" * 60)
    console.print("🧪 Enhanced Material Display Demo")
    console.print("=" * 60)
    enhanced_material_display(console)

    # Demo status display
    console.print("\n" + "=" * 60)
    console.print("📊 Enhanced Status Display Demo")
    console.print("=" * 60)
    enhanced_status_display(console)

    # Summary
    console.print("\n" + "=" * 60)
    summary_text = Text()
    summary_text.append("✨ ", style="yellow")
    summary_text.append("Enhanced UI Integration Complete!", style="green bold")
    summary_text.append("\n\nKey Benefits:\n", style="dim")
    summary_text.append("• Professional gradient ASCII art headers\n", style="blue")
    summary_text.append("• Sophisticated color-coded chat interface\n", style="cyan")
    summary_text.append("• Beautiful material formula displays\n", style="purple")
    summary_text.append("• Comprehensive status information\n", style="yellow")
    summary_text.append("• Responsive design for all terminal sizes\n", style="green")

    summary_panel = Panel(
        summary_text,
        title="[bold]Integration Summary[/bold]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(summary_panel)

    console.print("\n" + "=" * 60)
    console.print("🎯 Ready for integration with existing CrystaLyse.AI CLI!")
    console.print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

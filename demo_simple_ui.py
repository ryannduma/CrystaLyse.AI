#!/usr/bin/env python3
"""
Simple demo script for the enhanced CrystaLyse.AI UI components.
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

from crystalyse.ui.ascii_art import get_responsive_logo
from crystalyse.ui.gradients import create_gradient_text, GradientStyle

def main():
    """Run the simple UI demo."""
    console = Console()

    print("🎨 CrystaLyse.AI Enhanced UI Demo")
    print("=" * 50)

    # Clear screen
    console.clear()

    # Get responsive logo
    terminal_width = console.size.width
    logo = get_responsive_logo(terminal_width)

    # Create gradient text for the logo
    try:
        gradient_logo = create_gradient_text("CrystaLyse.AI", GradientStyle.CRYSTALYSE_BLUE)
        console.print(Panel(
            Align.center(gradient_logo),
            title="Gradient Text Demo",
            border_style="blue",
            box=ROUNDED
        ))
    except Exception as e:
        console.print(f"Gradient text error: {e}")
        console.print(Panel(
            Align.center(Text("CrystaLyse.AI", style="bold blue")),
            title="Fallback Text",
            border_style="blue",
            box=ROUNDED
        ))

    # Show ASCII art logo
    console.print(Panel(
        Align.center(Text(logo, style="blue")),
        title="ASCII Art Logo",
        border_style="cyan",
        box=ROUNDED,
        padding=(1, 2)
    ))

    # Demo chat interface
    console.print(Panel(
        "➤ Find a lead-free perovskite for solar cell applications",
        title="[bold cyan]You[/bold cyan]",
        border_style="cyan",
        padding=(0, 1)
    ))

    # Show progress
    with console.status("[bold green]Analyzing materials database...", spinner="dots"):
        time.sleep(2)

    # Demo response
    console.print(Panel(
        "🔬 Based on your query, I recommend exploring cesium tin iodide (CsSnI₃) "
        "and related tin halide perovskites. These materials offer excellent "
        "optoelectronic properties while avoiding toxic lead content.",
        title="[bold green]CrystaLyse.AI[/bold green]",
        border_style="green",
        padding=(0, 1)
    ))

    # Demo material result
    material_panel = Panel(
        Text.from_markup(
            "[bold blue]CsSnI₃[/bold blue]\n\n"
            "[dim]Properties:[/dim]\n"
            "• Band Gap: [green]1.3 eV[/green]\n"
            "• Formation Energy: [green]-0.45 eV/atom[/green]\n"
            "• Stability: [green]Stable[/green]\n"
            "• Crystal System: [green]Orthorhombic[/green]"
        ),
        title="[bold]Material Discovery Result[/bold]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(material_panel)

    # Demo system messages
    console.print(Panel(
        "✅ Analysis completed successfully!",
        title="[bold]System[/bold]",
        border_style="green",
        padding=(0, 1)
    ))

    console.print(Panel(
        "ℹ️ Results cached for future queries",
        title="[bold]System[/bold]",
        border_style="blue",
        padding=(0, 1)
    ))

    # Demo status bar
    status_text = Text()
    status_text.append("Model: ", style="dim")
    status_text.append("gpt-4", style="blue")
    status_text.append(" | Session: ", style="dim")
    status_text.append("ui_demo", style="cyan")
    status_text.append(" | User: ", style="dim")
    status_text.append("demo_user", style="green")

    console.print(Panel(
        status_text,
        title="Status",
        border_style="dim",
        padding=(0, 1)
    ))

    # Show completion message
    console.print(Panel(
        Text.from_markup(
            "✨ [bold green]UI Enhancement Demo Complete![/bold green]\n\n"
            "The enhanced UI provides:\n"
            "• [blue]Gradient ASCII art headers[/blue]\n"
            "• [purple]Professional theming system[/purple]\n"
            "• [cyan]Enhanced chat interface[/cyan]\n"
            "• [green]Scientific result formatting[/green]\n"
            "• [yellow]Responsive design[/yellow]\n"
            "• [red]Multiple theme options[/red]"
        ),
        title="[bold]Demo Summary[/bold]",
        border_style="green",
        padding=(1, 2)
    ))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

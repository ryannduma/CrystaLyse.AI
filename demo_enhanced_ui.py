#!/usr/bin/env python3
"""
Demo script to showcase the enhanced UI components working with CrystaLyse.AI
"""

import sys
from pathlib import Path

# Add the CrystaLyse.AI directory to the Python path
crystalyse_dir = Path(__file__).parent
sys.path.insert(0, str(crystalyse_dir))

def main():
    """Demo the enhanced UI components."""
    print("🔬 CrystaLyse.AI Enhanced UI Demo\n")
    
    try:
        from rich.console import Console
        from crystalyse.ui.themes import ThemeManager, ThemeType
        from crystalyse.ui.components import CrystaLyseHeader, ChatDisplay, MaterialDisplay
        from crystalyse.ui.gradients import create_gradient_text, GradientStyle
        
        # Initialize enhanced UI with red theme
        theme_manager = ThemeManager(ThemeType.CRYSTALYSE_RED)
        console = Console(theme=theme_manager.current_theme.rich_theme)
        
        # Demo 1: Enhanced Header
        print("Demo 1: Enhanced Header")
        header = CrystaLyseHeader(console)
        header_panel = header.render("1.0.0")
        console.print(header_panel)
        
        # Demo 2: Gradient Text
        print("\nDemo 2: Gradient Text")
        gradient_text = create_gradient_text(
            "CrystaLyse.AI Enhanced UI",
            GradientStyle.CRYSTALYSE_RED
        )
        console.print(gradient_text)
        
        # Demo 3: Chat Display
        print("\nDemo 3: Chat Display")
        chat_display = ChatDisplay(console)
        user_msg = chat_display.render_user_message("Find a novel photocatalyst for water splitting")
        assistant_msg = chat_display.render_assistant_message("Based on your query, I recommend exploring Sr2TiO3S - a layered Ruddlesden-Popper oxide-sulfide...")
        console.print(user_msg)
        console.print(assistant_msg)
        
        # Demo 4: Material Display
        print("\nDemo 4: Material Display")
        material_display = MaterialDisplay(console)
        sample_material = {
            "formula": "Sr2TiO3S",
            "properties": {
                "Formation Energy": {"value": -5.91, "unit": "eV/atom"},
                "Crystal System": {"value": "Orthorhombic", "unit": ""},
                "Space Group": {"value": "Pnma", "unit": ""},
                "Band Gap": {"value": 1.8, "unit": "eV"}
            }
        }
        
        material_panel = material_display.render_material_result(sample_material)
        console.print(material_panel)
        
        print("\n🎉 Enhanced UI Demo Complete!")
        print("✅ All components working correctly with red theme")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

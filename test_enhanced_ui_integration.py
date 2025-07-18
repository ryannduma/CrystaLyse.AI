#!/usr/bin/env python3
"""
Test script to verify enhanced UI integration with CrystaLyse.AI CLI
"""

import sys
import os
from pathlib import Path

# Add the CrystaLyse.AI directory to the Python path
crystalyse_dir = Path(__file__).parent
sys.path.insert(0, str(crystalyse_dir))

def test_enhanced_ui_imports():
    """Test that enhanced UI components can be imported successfully."""
    print("Testing enhanced UI imports...")
    
    try:
        from crystalyse.ui.themes import ThemeManager, ThemeType
        from crystalyse.ui.components import CrystaLyseHeader, ChatDisplay, MaterialDisplay
        from crystalyse.ui.gradients import create_gradient_text, GradientStyle
        print("✅ Enhanced UI imports successful")
        return True
    except ImportError as e:
        print(f"❌ Enhanced UI import failed: {e}")
        return False

def test_theme_initialization():
    """Test that the red theme initializes correctly."""
    print("Testing theme initialization...")
    
    try:
        from crystalyse.ui.themes import ThemeManager, ThemeType
        theme_manager = ThemeManager(ThemeType.CRYSTALYSE_RED)
        
        # Check that theme is properly initialized
        assert theme_manager.theme_type == ThemeType.CRYSTALYSE_RED
        assert theme_manager.current_theme is not None
        assert theme_manager.current_theme.colors.accent_red is not None
        
        print("✅ Red theme initialization successful")
        return True
    except Exception as e:
        print(f"❌ Theme initialization failed: {e}")
        return False

def test_gradient_text():
    """Test gradient text generation."""
    print("Testing gradient text generation...")
    
    try:
        from crystalyse.ui.gradients import create_gradient_text, GradientStyle
        
        # Test gradient text creation
        gradient_text = create_gradient_text(
            "CrystaLyse.AI", 
            GradientStyle.CRYSTALYSE_RED
        )
        
        # Check that gradient text is created
        assert gradient_text is not None
        assert gradient_text.plain == "CrystaLyse.AI"
        
        print("✅ Gradient text generation successful")
        return True
    except Exception as e:
        print(f"❌ Gradient text generation failed: {e}")
        return False

def test_component_initialization():
    """Test that UI components initialize correctly."""
    print("Testing component initialization...")
    
    try:
        from rich.console import Console
        from crystalyse.ui.themes import ThemeManager, ThemeType
        from crystalyse.ui.components import CrystaLyseHeader, ChatDisplay, MaterialDisplay
        
        theme_manager = ThemeManager(ThemeType.CRYSTALYSE_RED)
        console = Console(theme=theme_manager.current_theme.rich_theme)
        
        # Test component initialization
        header = CrystaLyseHeader(console)
        chat_display = ChatDisplay(console)
        material_display = MaterialDisplay(console)
        
        # Test header rendering
        header_panel = header.render("1.0.0")
        assert header_panel is not None
        
        print("✅ Component initialization successful")
        return True
    except Exception as e:
        print(f"❌ Component initialization failed: {e}")
        return False

def test_cli_imports():
    """Test that CLI imports work with enhanced UI."""
    print("Testing CLI imports with enhanced UI...")
    
    try:
        from crystalyse.cli import cli
        print("✅ CLI imports with enhanced UI successful")
        return True
    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔬 Testing CrystaLyse.AI Enhanced UI Integration\n")
    
    tests = [
        test_enhanced_ui_imports,
        test_theme_initialization,
        test_gradient_text,
        test_component_initialization,
        test_cli_imports
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced UI integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
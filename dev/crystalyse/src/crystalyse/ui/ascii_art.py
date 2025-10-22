"""
ASCII Art for CrystaLyse.AI

Provides responsive ASCII art logos with gradient support.
"""

# Full CRYSTALYSE logo for wide terminals
CRYSTALYSE_FULL_LOGO = '''
 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗     █████╗ ██╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║    ╚██╗ ██╔╝██╔════╝██╔════╝    ██╔══██╗██║
██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║     ╚████╔╝ ███████╗█████╗      ███████║██║
██║     ██╔══██╗  ╚██╔╝  ╚════██║   ██║   ██╔══██║██║      ╚██╔╝  ╚════██║██╔══╝      ██╔══██║██║
╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗  ██║   ███████║███████╗    ██║  ██║██║
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝  ╚═╝   ╚══════╝╚══════╝    ╚═╝  ╚═╝╚═╝
'''

# Compact CRYSTALYSE logo for medium terminals
CRYSTALYSE_COMPACT_LOGO = '''
 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║    ╚██╗ ██╔╝██╔════╝██╔════╝
██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║     ╚████╔╝ ███████╗█████╗  
██║     ██╔══██╗  ╚██╔╝  ╚════██║   ██║   ██╔══██║██║      ╚██╔╝  ╚════██║██╔══╝  
╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗  ██║   ███████║███████╗
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝  ╚═╝   ╚══════╝╚══════╝
'''

# Minimal logo for small terminals
CRYSTALYSE_MINIMAL_LOGO = '''
 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║    ╚██╗ ██╔╝██╔════╝██╔════╝
██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║     ╚████╔╝ ███████╗█████╗  
╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗  ██║   ███████║███████╗
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝  ╚═╝   ╚══════╝╚══════╝
'''

# Ultra minimal for very small terminals
CRYSTALYSE_ULTRA_MINIMAL = '''
 ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║    ╚██╗ ██╔╝██╔════╝██╔════╝
╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗  ██║   ███████║███████╗
 ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝  ╚═╝   ╚══════╝╚══════╝
'''

# Default to compact for backwards compatibility
CRYSTALYSE_ASCII_ART = CRYSTALYSE_COMPACT_LOGO


def get_ascii_art_width(ascii_art: str) -> int:
    """Calculate the display width of ASCII art."""
    lines = ascii_art.strip().split('\n')
    return max(len(line) for line in lines) if lines else 0


def get_responsive_logo(terminal_width: int) -> str:
    """
    Get the appropriate logo size based on terminal width.
    
    Args:
        terminal_width: Current terminal width in characters
        
    Returns:
        ASCII art string appropriate for the terminal width
    """
    full_width = get_ascii_art_width(CRYSTALYSE_FULL_LOGO)
    compact_width = get_ascii_art_width(CRYSTALYSE_COMPACT_LOGO)
    minimal_width = get_ascii_art_width(CRYSTALYSE_MINIMAL_LOGO)
    ultra_minimal_width = get_ascii_art_width(CRYSTALYSE_ULTRA_MINIMAL)

    # Add some padding for readability
    padding = 10

    if terminal_width >= full_width + padding:
        return CRYSTALYSE_FULL_LOGO
    elif terminal_width >= compact_width + padding:
        return CRYSTALYSE_COMPACT_LOGO
    elif terminal_width >= minimal_width + padding:
        return CRYSTALYSE_MINIMAL_LOGO
    elif terminal_width >= ultra_minimal_width + padding:
        return CRYSTALYSE_ULTRA_MINIMAL
    else:
        # For very small terminals, use text fallback
        return "CrystaLyse.AI - Materials Discovery Platform"


def get_logo_with_subtitle(terminal_width: int, version: str = None) -> tuple[str, str]:
    """
    Get logo with appropriate subtitle based on terminal width.
    
    Args:
        terminal_width: Current terminal width in characters
        version: Optional version string
        
    Returns:
        Tuple of (logo, subtitle)
    """
    logo = get_responsive_logo(terminal_width)

    if version:
        subtitle = f"v{version} - AI-Powered Materials Discovery"
    else:
        subtitle = "AI-Powered Materials Discovery"

    return logo, subtitle

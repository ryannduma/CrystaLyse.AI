"""
Crystalyse command-line interface entry point.
"""

import sys
from pathlib import Path

# Add parent directory to path for direct execution
if __name__ == "__main__":
    parent_dir = Path(__file__).resolve().parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    from crystalyse.cli import main
    main()
else:
    from .cli import main
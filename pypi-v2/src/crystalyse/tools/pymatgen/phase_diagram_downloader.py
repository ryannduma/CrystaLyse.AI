"""
Phase diagram data management for PyMatGen calculations.

Handles automatic download from Figshare and caching in ~/.cache/crystalyse/
This provides:
- Zero-configuration setup (auto-download on first use)
- Standard cache location (~/.cache/crystalyse/phase_diagrams/)
- Support for custom data directories via environment variable
- Clean error handling and progress reporting

Materials Project database: 271,617 entries (170 MB)
"""

import logging
import os
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Figshare download URL for the phase diagram pickle file (170 MB)
# Using the share link from https://figshare.com/s/63a6a720e9ca576141fb
FIGSHARE_URL = "https://figshare.com/ndownloader/articles/28298439/versions/1"

# Default cache directory following XDG Base Directory specification
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "crystalyse" / "phase_diagrams"

# Expected filename
PHASE_DIAGRAM_FILENAME = "ppd-mp_all_entries_uncorrected_250409.pkl.gz"


def _download_file(url: str, filepath: Path) -> None:
    """
    Download a file from URL with progress bar.

    Args:
        url: URL to download from
        filepath: Local path to save file

    Raises:
        requests.HTTPError: If download fails
    """
    logger.info(f"Downloading phase diagram data from {url}")

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download phase diagram data: {e}") from e

    total_size = int(response.headers.get("content-length", 0))

    with open(filepath, "wb") as f, tqdm(
        desc=f"Downloading {filepath.name}",
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))

    logger.info(f"Download complete: {filepath}")


def ensure_phase_diagram_downloaded(cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """
    Ensure phase diagram data is downloaded to cache directory.

    This function:
    1. Checks if phase diagram data already exists in cache
    2. If not, downloads from Figshare
    3. Returns path to the data file

    Args:
        cache_dir: Directory to store data (default: ~/.cache/crystalyse/phase_diagrams/)

    Returns:
        Path to phase diagram data file

    Raises:
        RuntimeError: If download fails
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    data_file = cache_dir / PHASE_DIAGRAM_FILENAME

    # Check if file already exists
    if data_file.exists() and data_file.stat().st_size > 0:
        logger.info(f"Phase diagram data found in cache: {data_file}")
        return data_file

    # Need to download
    logger.info(f"Phase diagram data not found in {cache_dir}")
    logger.info(
        "Downloading Materials Project database (170 MB, 271,617 entries, one-time download)..."
    )

    try:
        _download_file(FIGSHARE_URL, data_file)
        logger.info(f"Phase diagram data setup complete: {data_file}")

    except Exception as e:
        # Clean up partial downloads
        if data_file.exists():
            data_file.unlink()
        raise RuntimeError(f"Phase diagram data download failed: {e}") from e

    # Verify file exists after download
    if not data_file.exists():
        raise RuntimeError(
            f"Phase diagram data not found after download: {data_file}\n"
            f"This may indicate a corrupted download. Try removing {cache_dir} and retrying."
        )

    return data_file


def get_phase_diagram_path(custom_path: Optional[str] = None) -> Path:
    """
    Get phase diagram data path, downloading if needed.

    This is the main entry point for phase diagram data management. It:
    1. Checks for custom data path (via argument or CRYSTALYSE_PPD_PATH env var)
    2. If custom path specified, validates file exists there
    3. Otherwise, uses standard cache location and auto-downloads if needed

    Args:
        custom_path: Optional custom phase diagram data file path or directory

    Returns:
        Path to phase diagram data file

    Raises:
        FileNotFoundError: If file not found in custom path
        RuntimeError: If download fails

    Example:
        >>> # Auto-download to cache (zero configuration)
        >>> path = get_phase_diagram_path()
        >>>
        >>> # Use custom file
        >>> path = get_phase_diagram_path(custom_path="/my/data/ppd.pkl.gz")
        >>>
        >>> # Use environment variable
        >>> os.environ['CRYSTALYSE_PPD_PATH'] = '/my/data'
        >>> path = get_phase_diagram_path()
    """
    # Check for custom path from argument or environment variable
    custom = custom_path or os.getenv("CRYSTALYSE_PPD_PATH")

    if custom:
        custom_pathobj = Path(custom)

        # If it's a directory, look for the expected filename inside
        if custom_pathobj.is_dir():
            custom_pathobj = custom_pathobj / PHASE_DIAGRAM_FILENAME

        if not custom_pathobj.exists():
            raise FileNotFoundError(
                f"Phase diagram data not found at custom path: {custom_pathobj}\n"
                f"Expected file: {PHASE_DIAGRAM_FILENAME}\n"
                f"Either provide the correct path or remove CRYSTALYSE_PPD_PATH to use auto-download."
            )

        logger.info(f"Using custom phase diagram data: {custom_pathobj}")
        return custom_pathobj

    # Use standard cache location with auto-download
    data_path = ensure_phase_diagram_downloaded()
    logger.info(f"Using cached phase diagram data: {data_path}")
    return data_path


# Fallback paths for backward compatibility (checked in order)
FALLBACK_PATHS = [
    Path("/home/ryan/updatecrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz"),
    Path("/home/ryan/mycrystalyse/CrystaLyse.AI/ppd-mp_all_entries_uncorrected_250409.pkl.gz"),
    Path(__file__).parent.parent.parent.parent.parent / "ppd-mp_all_entries_uncorrected_250409.pkl.gz",
    Path.home() / "updatecrystalyse" / "CrystaLyse.AI" / "ppd-mp_all_entries_uncorrected_250409.pkl.gz",
]


def get_phase_diagram_path_with_fallbacks(custom_path: Optional[str] = None) -> Path:
    """
    Get phase diagram path with fallback to legacy locations.

    This function tries multiple strategies in order:
    1. Custom path (argument or CRYSTALYSE_PPD_PATH env var)
    2. Auto-download to cache
    3. Legacy fallback paths (for development/existing installations)

    Args:
        custom_path: Optional custom phase diagram data file path

    Returns:
        Path to phase diagram data file

    Raises:
        FileNotFoundError: If file not found anywhere
    """
    # Try standard method first (custom path or auto-download)
    try:
        return get_phase_diagram_path(custom_path)
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Standard lookup failed: {e}")
        logger.info("Trying fallback paths for backward compatibility...")

    # Try fallback paths
    for fallback_path in FALLBACK_PATHS:
        if fallback_path.exists():
            logger.info(f"Using fallback path: {fallback_path}")
            return fallback_path

    # Nothing worked
    raise FileNotFoundError(
        f"Phase diagram data not found.\n"
        f"Tried:\n"
        f"  1. Custom path: {custom_path or os.getenv('CRYSTALYSE_PPD_PATH') or 'None'}\n"
        f"  2. Auto-download to: {DEFAULT_CACHE_DIR / PHASE_DIAGRAM_FILENAME}\n"
        f"  3. Fallback paths: {FALLBACK_PATHS}\n\n"
        f"To fix:\n"
        f"  - Set CRYSTALYSE_PPD_PATH environment variable to the file location\n"
        f"  - Or ensure internet connection for auto-download\n"
        f"  - Or manually download from: {FIGSHARE_URL}"
    )

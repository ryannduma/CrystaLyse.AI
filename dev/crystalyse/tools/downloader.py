"""
Downloader for external data dependencies.
"""

import hashlib
import logging
import sys
from pathlib import Path

import requests
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

logger = logging.getLogger(__name__)

# Constants
CACHE_DIR = Path.home() / ".cache" / "crystalyse"
PHASE_DIAGRAM_FILENAME = "ppd-mp_all_entries_uncorrected_250409.pkl.gz"
PHASE_DIAGRAM_URL = "https://ndownloader.figshare.com/files/59229653"
PHASE_DIAGRAM_MD5 = "47a39876d3cf68d0da1d8335b32ce195"


def get_phase_diagram_path() -> Path:
    """Get the expected path for the phase diagram file in the cache."""
    return CACHE_DIR / PHASE_DIAGRAM_FILENAME


def verify_checksum(file_path: Path, expected_md5: str) -> bool:
    """Verify the MD5 checksum of a file."""
    if not file_path.exists():
        return False

    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest() == expected_md5


def ensure_phase_diagram_data(force: bool = False) -> Path:
    """
    Ensure the phase diagram data file exists.
    Downloads it if missing or invalid.

    Args:
        force: Force download even if file exists.

    Returns:
        Path to the data file.
    """
    target_path = get_phase_diagram_path()

    if target_path.exists() and not force:
        # Verify checksum to ensure integrity
        if verify_checksum(target_path, PHASE_DIAGRAM_MD5):
            logger.debug(f"Phase diagram data found and verified at {target_path}")
            return target_path
        else:
            logger.warning(
                f"Phase diagram data at {target_path} has invalid checksum. Re-downloading."
            )

    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading phase diagram data to {target_path}...")

    try:
        with requests.get(PHASE_DIAGRAM_URL, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("Downloading Phase Diagram Data...", total=total_size)

                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        # Verify download
        if verify_checksum(target_path, PHASE_DIAGRAM_MD5):
            logger.info("Download completed and verified successfully.")
            return target_path
        else:
            logger.error("Download completed but checksum verification failed.")
            # Don't delete it, maybe the checksum changed or it's a partial download that can be inspected
            raise RuntimeError("Downloaded file checksum mismatch")

    except Exception as e:
        logger.error(f"Failed to download phase diagram data: {e}")
        if target_path.exists():
            # Clean up partial download
            target_path.unlink()
        raise


if __name__ == "__main__":
    # Allow running as a script
    logging.basicConfig(level=logging.INFO)
    try:
        path = ensure_phase_diagram_data()
        print(f"Data available at: {path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

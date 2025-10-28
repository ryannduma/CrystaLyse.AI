"""
Checkpoint management for Chemeleon models.

Handles automatic download from Figshare and caching in ~/.cache/crystalyse/
This replaces the buggy upstream download_util to provide:
- Zero-configuration setup (auto-download on first use)
- Standard cache location (~/.cache/crystalyse/chemeleon_checkpoints/)
- Support for custom checkpoint directories via environment variable
- Clean error handling and progress reporting
"""

import tarfile
import logging
from pathlib import Path
from typing import Dict, Optional

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Figshare download URL for the checkpoint tar.gz file (523 MB)
FIGSHARE_URL = "https://figshare.com/ndownloader/files/54966305"

# Default cache directory following XDG Base Directory specification
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "crystalyse" / "chemeleon_checkpoints"

# Expected checkpoint filenames for each task
CHECKPOINT_FILENAMES = {
    "csp": "chemeleon_csp_alex_mp_20_v0.0.2.ckpt",  # Crystal Structure Prediction
    "dng": "chemeleon_dng_alex_mp_20_v0.0.2.ckpt",  # De Novo Generation
}


def _download_file(url: str, filepath: Path) -> None:
    """
    Download a file from URL with progress bar.

    Args:
        url: URL to download from
        filepath: Local path to save file

    Raises:
        requests.HTTPError: If download fails
    """
    logger.info(f"Downloading checkpoint from {url}")

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download checkpoint: {e}") from e

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


def _extract_tar_gz(filepath: Path, extract_to: Path) -> None:
    """
    Extract tar.gz file to specified directory.

    Args:
        filepath: Path to tar.gz file
        extract_to: Directory to extract to

    Raises:
        tarfile.TarError: If extraction fails
    """
    logger.info(f"Extracting {filepath} to {extract_to}")

    try:
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(path=extract_to)
    except tarfile.TarError as e:
        raise RuntimeError(f"Failed to extract checkpoint archive: {e}") from e

    logger.info(f"Extraction complete")


def ensure_checkpoints_downloaded(cache_dir: Path = DEFAULT_CACHE_DIR) -> Dict[str, Path]:
    """
    Ensure all checkpoints are downloaded to cache directory.

    This function:
    1. Checks if checkpoints already exist in cache
    2. If not, downloads the checkpoint archive from Figshare
    3. Extracts checkpoints to cache directory
    4. Cleans up the archive file
    5. Returns dict mapping task names to checkpoint paths

    Args:
        cache_dir: Directory to store checkpoints (default: ~/.cache/crystalyse/chemeleon_checkpoints/)

    Returns:
        Dict mapping task ("csp", "dng") to checkpoint file paths

    Raises:
        RuntimeError: If download or extraction fails
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Build expected checkpoint paths
    checkpoint_paths = {
        task: cache_dir / filename
        for task, filename in CHECKPOINT_FILENAMES.items()
    }

    # Check if all checkpoints already exist
    if all(path.exists() and path.stat().st_size > 0 for path in checkpoint_paths.values()):
        logger.info(f"Checkpoints found in cache: {cache_dir}")
        return checkpoint_paths

    # Need to download
    logger.info(f"Checkpoints not found in {cache_dir}")
    logger.info("Downloading checkpoint archive from Figshare (523 MB, one-time download)...")

    # Download tar.gz file
    tar_file = cache_dir / "checkpoints.tar.gz"
    try:
        _download_file(FIGSHARE_URL, tar_file)

        # Extract to cache directory
        logger.info("Extracting checkpoint files...")
        _extract_tar_gz(tar_file, cache_dir.parent)  # Extracts to parent, creates ckpts/ or chemeleon_checkpoints/

        # Clean up tar file
        tar_file.unlink()
        logger.info(f"Checkpoint setup complete: {cache_dir}")

    except Exception as e:
        # Clean up partial downloads
        if tar_file.exists():
            tar_file.unlink()
        raise RuntimeError(f"Checkpoint download failed: {e}") from e

    # Verify all checkpoints exist after extraction
    for task, path in checkpoint_paths.items():
        if not path.exists():
            raise RuntimeError(
                f"Checkpoint {task} not found after extraction: {path}\n"
                f"This may indicate a corrupted download. Try removing {cache_dir} and retrying."
            )

    return checkpoint_paths


def get_checkpoint_path(task: str, custom_dir: Optional[str] = None) -> Path:
    """
    Get checkpoint path for a task, downloading if needed.

    This is the main entry point for checkpoint management. It:
    1. Checks for custom checkpoint directory (via argument or CHEMELEON_CHECKPOINT_DIR env var)
    2. If custom dir specified, validates checkpoint exists there
    3. Otherwise, uses standard cache location and auto-downloads if needed

    Args:
        task: Task name ("csp" for crystal structure prediction, "dng" for de novo generation)
        custom_dir: Optional custom checkpoint directory path

    Returns:
        Path to checkpoint file

    Raises:
        ValueError: If task name is invalid
        FileNotFoundError: If checkpoint not found in custom directory
        RuntimeError: If download or extraction fails

    Example:
        >>> # Auto-download to cache (zero configuration)
        >>> path = get_checkpoint_path("csp")
        >>>
        >>> # Use custom directory
        >>> path = get_checkpoint_path("csp", custom_dir="/my/checkpoints")
    """
    # Validate task name
    if task not in CHECKPOINT_FILENAMES:
        raise ValueError(
            f"Invalid task: {task}. Must be one of: {list(CHECKPOINT_FILENAMES.keys())}"
        )

    if custom_dir:
        # User specified custom checkpoint directory
        custom_path = Path(custom_dir) / CHECKPOINT_FILENAMES[task]
        if not custom_path.exists():
            raise FileNotFoundError(
                f"Checkpoint not found in custom directory: {custom_path}\n"
                f"Expected file: {CHECKPOINT_FILENAMES[task]}\n"
                f"Either provide the correct path or remove CHEMELEON_CHECKPOINT_DIR to use auto-download."
            )
        logger.info(f"Using custom checkpoint: {custom_path}")
        return custom_path

    # Use standard cache location with auto-download
    checkpoints = ensure_checkpoints_downloaded()
    checkpoint_path = checkpoints[task]
    logger.info(f"Using cached checkpoint: {checkpoint_path}")
    return checkpoint_path

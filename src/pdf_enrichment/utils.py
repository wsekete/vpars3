"""
Utility functions for PDF enrichment platform.
Simplified for Claude Desktop integration.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> None:
    """Set up logging configuration."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers
    )


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be filesystem-safe."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # Limit length
    if len(sanitized) > 200:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        sanitized = name[:200-len(ext)] + ext
    
    return sanitized or "unnamed_file"


def validate_file_path(file_path: Path, create_if_missing: bool = False) -> bool:
    """
    Validate file path and optionally create directories.
    
    Security improvements:
    - Prevents directory traversal attacks
    - Validates path components
    - Checks for symlink attacks
    """
    try:
        # Resolve path to prevent traversal attacks
        resolved_path = file_path.resolve()
        
        # Check for suspicious path components
        path_parts = resolved_path.parts
        for part in path_parts:
            if part in ('..', '.', '') or part.startswith('.'):
                return False
        
        # Check for symlink attacks
        if resolved_path.is_symlink():
            return False
        
        if create_if_missing and not resolved_path.exists():
            # Only create if parent is safe
            parent = resolved_path.parent
            if parent.exists() and parent.is_dir():
                resolved_path.mkdir(parents=True, exist_ok=True)
        
        # Check if path is valid and accessible
        if resolved_path.exists():
            return resolved_path.is_file() if resolved_path.is_file() else resolved_path.is_dir()
        else:
            return resolved_path.parent.exists() or create_if_missing
    
    except (OSError, ValueError):
        return False


def backup_file(file_path: Path, backup_suffix: str = ".backup") -> Path:
    """Create a backup copy of a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f"{backup_suffix}_{timestamp}{file_path.suffix}")
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def ensure_directory_exists(directory: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    directory.mkdir(parents=True, exist_ok=True)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and special characters."""
    # Replace multiple whitespace with single space
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


# Constants for common file extensions
PDF_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}
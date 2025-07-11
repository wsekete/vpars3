"""
Utility functions for PDF enrichment platform.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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
    """Validate file path and optionally create directories."""
    try:
        if create_if_missing and not file_path.exists():
            file_path.mkdir(parents=True, exist_ok=True)
        
        # Check if path is valid and accessible
        if file_path.exists():
            return file_path.is_file() if file_path.is_file() else file_path.is_dir()
        else:
            return file_path.parent.exists() or create_if_missing
    
    except Exception:
        return False


def backup_file(file_path: Path, backup_suffix: str = ".backup") -> Path:
    """Create a backup copy of a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f"{backup_suffix}_{timestamp}{file_path.suffix}")
    
    shutil.copy2(file_path, backup_path)
    return backup_path


def calculate_confidence_score(factors: Dict[str, Union[int, float, bool]]) -> str:
    """Calculate confidence score from various factors."""
    score = 0
    max_score = 0
    
    for factor, value in factors.items():
        if isinstance(value, bool):
            score += 1 if value else 0
            max_score += 1
        elif isinstance(value, (int, float)):
            score += value
            max_score += 1
    
    if max_score == 0:
        return "low"
    
    ratio = score / max_score
    if ratio >= 0.8:
        return "high"
    elif ratio >= 0.5:
        return "medium"
    else:
        return "low"


def validate_bem_name_format(name: str) -> tuple[bool, str]:
    """Validate BEM name format and return validation result."""
    if not name:
        return False, "Name cannot be empty"
    
    # Check basic pattern
    if not re.match(r'^[a-z][a-z0-9-]*_[a-z][a-z0-9-]*(?:__[a-z][a-z0-9-]*|--group)?$', name):
        return False, "Name must follow BEM format: block_element or block_element__modifier or block_element--group"
    
    # Check for reserved words
    reserved = {'class', 'id', 'name', 'type', 'value', 'checked', 'selected', 'disabled', 'readonly'}
    parts = name.replace('__', '_').replace('--', '_').split('_')
    
    for part in parts:
        if part in reserved:
            return False, f"'{part}' is a reserved word and cannot be used"
    
    # Check length
    if len(name) > 100:
        return False, "Name is too long (maximum 100 characters)"
    
    return True, "Valid BEM name"


def normalize_field_name(name: str) -> str:
    """Normalize field name for comparison."""
    # Convert to lowercase
    normalized = name.lower()
    
    # Replace common separators with underscores
    normalized = re.sub(r'[-\s.]+', '_', normalized)
    
    # Remove special characters except underscores
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    # Remove multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


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


def extract_form_metadata_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """Extract form metadata from filename."""
    patterns = {
        'form_id': [
            r'(\d{4}[A-Z]?)',  # 1234A
            r'([A-Z]{2,4}-\d{4})',  # ABC-1234
            r'(Form[_-]?\d+)',  # Form123
        ],
        'version': [
            r'[vV](\d+(?:\.\d+)*)',  # v1.2.3
            r'_(\d+(?:\.\d+)*)$',  # _1.2
        ],
        'date': [
            r'(\d{4}[-_]\d{2}[-_]\d{2})',  # 2024-01-01
            r'(\d{2}[-_]\d{2}[-_]\d{4})',  # 01-01-2024
        ],
    }
    
    metadata = {}
    
    for key, pattern_list in patterns.items():
        found = False
        for pattern in pattern_list:
            match = re.search(pattern, filename)
            if match:
                metadata[key] = match.group(1)
                found = True
                break
        
        if not found:
            metadata[key] = None
    
    return metadata


# Constants for common file extensions and patterns
PDF_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}

# Common form field patterns
FORM_FIELD_PATTERNS = {
    'name': r'(first|last|middle|full)[-_]?name',
    'address': r'(street|address|addr)[-_]?(line|1|2)?',
    'city': r'city',
    'state': r'state|st',
    'zip': r'zip|postal[-_]?code',
    'phone': r'(phone|tel|telephone)[-_]?(number)?',
    'email': r'email|e[-_]?mail',
    'ssn': r'ssn|social[-_]?security[-_]?number',
    'date': r'date|dob|birth[-_]?date',
    'signature': r'sign|signature',
    'amount': r'amount|amt|value|total',
    'percent': r'percent|pct|percentage',
    'checkbox': r'check|box|option',
    'radio': r'radio|choice|select',
}

# BEM naming conventions
BEM_BLOCK_SUGGESTIONS = {
    'personal': ['owner-information', 'contact-information', 'personal-details'],
    'address': ['address-information', 'mailing-address', 'contact-address'],
    'payment': ['payment-information', 'billing-information', 'financial-details'],
    'beneficiary': ['beneficiary-information', 'beneficiary-details'],
    'employment': ['employment-information', 'employer-details'],
    'medical': ['medical-information', 'health-details'],
    'signature': ['signatures', 'authorization', 'consent'],
    'change': ['change-request', 'modification-request', 'update-request'],
}

# Default confidence thresholds
CONFIDENCE_THRESHOLDS = {
    'high': 0.8,
    'medium': 0.5,
    'low': 0.0,
}

"""
Core functionality for VyerWall GUI
"""
from .config_manager import (
    config_bp,
    mark_config_dirty,
    mark_config_clean,
    is_config_dirty
)

__all__ = [
    'config_bp',
    'mark_config_dirty',
    'mark_config_clean',
    'is_config_dirty'
]

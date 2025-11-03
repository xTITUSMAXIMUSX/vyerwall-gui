"""
Firewall rules and zones management module
"""
from .rules.views import rules_bp
from .zone.views import zone_bp

__all__ = ["rules_bp", "zone_bp"]

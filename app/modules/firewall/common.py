from __future__ import annotations

from typing import Any, Dict

from flask import current_app

from app.modules.firewall.rules.utils import ensure_mapping


def load_firewall_root() -> Dict[str, Any]:
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "ipv4"])
        return ensure_mapping(getattr(response, "result", {}) or {})
    except Exception:
        return {}

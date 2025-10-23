import re
from typing import Any, Dict, List, Optional, Set

from flask import current_app

from .util import normalise_iface_name

ZoneConfig = Dict[str, Dict[str, Any]]


def _merge_container(container: Any) -> Dict[str, Any]:
    if isinstance(container, dict):
        return container
    if isinstance(container, list):
        merged: Dict[str, Any] = {}
        for entry in container:
            if isinstance(entry, dict):
                merged.update(entry)
        return merged
    return {}


def load_zone_config() -> ZoneConfig:
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "zone"])
        result = getattr(response, "result", {}) or {}
    except Exception:
        result = {}
    merged = _merge_container(result)
    if "zone" in merged and isinstance(merged["zone"], (dict, list)):
        return _merge_container(merged["zone"])
    return merged


def _interface_members(member_block: Any) -> Set[str]:
    interfaces: Set[str] = set()
    if isinstance(member_block, dict):
        interface_block = member_block.get("interface")
        if isinstance(interface_block, dict):
            for key in interface_block.keys():
                interfaces.add(str(key))
        elif isinstance(interface_block, list):
            for entry in interface_block:
                if isinstance(entry, dict):
                    interfaces.update(str(key) for key in entry.keys())
                elif entry:
                    interfaces.add(str(entry))
        elif isinstance(interface_block, str):
            interfaces.add(interface_block)
    elif isinstance(member_block, list):
        for entry in member_block:
            interfaces.update(_interface_members(entry))
    elif isinstance(member_block, str):
        interfaces.add(member_block)
    return interfaces


def list_zones(zone_config: Optional[ZoneConfig] = None) -> List[str]:
    config = zone_config if zone_config is not None else load_zone_config()
    zones = sorted(config.keys(), key=lambda item: item.lower())
    return zones


def map_zone_members(zone_config: Optional[ZoneConfig] = None) -> Dict[str, Set[str]]:
    config = zone_config if zone_config is not None else load_zone_config()
    membership: Dict[str, Set[str]] = {}
    for zone_name, zone_cfg in config.items():
        if not isinstance(zone_cfg, dict):
            continue
        members = _interface_members(zone_cfg.get("member"))
        membership[zone_name] = {normalise_iface_name(name) or name for name in members}
    return membership


def find_zone_for_interface(iface: str, zone_config: Optional[ZoneConfig] = None) -> Optional[str]:
    iface_normalised = normalise_iface_name(iface) or iface
    membership = map_zone_members(zone_config)
    for zone_name, members in membership.items():
        if iface_normalised in members:
            return zone_name
    return None


def sanitise_zone_name(name: str) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned.upper()


def build_zone_definition_commands(zone: str, existing_config: Optional[ZoneConfig] = None) -> List[List[str]]:
    zone_name = sanitise_zone_name(zone)
    if not zone_name:
        return []
    config = existing_config if existing_config is not None else load_zone_config()
    if zone_name in config:
        return []

    commands: List[List[str]] = [["firewall", "zone", zone_name]]
    if zone_name == "LOCAL":
        commands.append(["firewall", "zone", zone_name, "local-zone"])
    commands.append(["firewall", "zone", zone_name, "default-action", "drop"])
    return commands


def build_zone_membership_commands(zone: str, iface: str) -> List[List[str]]:
    zone_name = sanitise_zone_name(zone)
    iface_name = normalise_iface_name(iface) or iface
    if not zone_name or not iface_name:
        return []
    return [["firewall", "zone", zone_name, "member", "interface", iface_name]]


def build_zone_membership_delete(zone: str, iface: str) -> List[List[str]]:
    zone_name = sanitise_zone_name(zone)
    iface_name = normalise_iface_name(iface) or iface
    if not zone_name or not iface_name:
        return []
    return [["firewall", "zone", zone_name, "member", "interface", iface_name]]


def zone_pair_firewall_name(source_zone: str, destination_zone: str) -> str:
    src = sanitise_zone_name(source_zone)
    dst = sanitise_zone_name(destination_zone)
    return f"{src}-{dst}"


def build_zone_binding_commands(source_zone: str, destination_zone: str, firewall_name: str) -> List[List[str]]:
    src = sanitise_zone_name(source_zone)
    dst = sanitise_zone_name(destination_zone)
    if not src or not dst or not firewall_name:
        return []
    return [["firewall", "zone", dst, "from", src, "firewall", "name", firewall_name]]

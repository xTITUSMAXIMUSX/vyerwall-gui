from __future__ import annotations

from typing import Any, Dict, Iterable, List

from flask import current_app

from app.modules.interfaces.utils import normalise_iface_name
from app.modules.interfaces.zone import load_zone_config, map_zone_members, sanitise_zone_name

from app.modules.firewall.rules.utils import ensure_mapping


def build_zone_map() -> Dict[str, Dict[str, str]]:
    try:
        zone_config = load_zone_config()
    except Exception:
        zone_config = {}

    mapping: Dict[str, Dict[str, str]] = {}
    zone_container = ensure_mapping(zone_config)

    def _extract_names(raw_entry) -> List[str]:
        names: List[str] = []
        if isinstance(raw_entry, dict):
            names.extend(str(key) for key in raw_entry.keys())
        elif isinstance(raw_entry, list):
            for entry in raw_entry:
                if isinstance(entry, dict):
                    names.extend(str(key) for key in entry.keys())
                elif entry:
                    names.append(str(entry))
        elif isinstance(raw_entry, str):
            names.append(raw_entry)
        return names

    def _record_firewall(raw_entry, source_name: str, destination_name: str):
        for firewall_name in _extract_names(raw_entry):
            name_str = str(firewall_name or "").strip()
            if not name_str:
                continue
            mapping[name_str] = {
                "source_zone": source_name,
                "destination_zone": destination_name,
                "zone_label": f"{source_name} -> {destination_name}",
            }

    for destination_zone, destination_cfg in zone_container.items():
        destination_name = sanitise_zone_name(destination_zone)
        if not destination_name:
            continue

        from_container = ensure_mapping(destination_cfg.get("from"))
        for source_zone, source_cfg in from_container.items():
            source_name = sanitise_zone_name(source_zone)
            if not source_name:
                continue

            firewall_container = ensure_mapping(source_cfg.get("firewall"))
            raw_names = firewall_container.get("name")
            _record_firewall(raw_names, source_name, destination_name)

        intra_container = ensure_mapping(destination_cfg.get("intra-zone-filtering"))
        intra_firewall = ensure_mapping(intra_container.get("firewall"))
        intra_names = intra_firewall.get("name")
        if intra_names:
            _record_firewall(intra_names, destination_name, destination_name)

    return mapping


def list_unassigned_interfaces() -> Iterable[str]:
    zone_config = load_zone_config() or {}
    membership = map_zone_members(zone_config)
    assigned = {
        (normalise_iface_name(member) or member).lower()
        for members in membership.values()
        for member in members
    }

    device = getattr(current_app, "device", None)
    if not device:
        return []
    try:
        response = device.retrieve_show_config(path=["interfaces"])
        iface_config = ensure_mapping(getattr(response, "result", {}) or {})
    except Exception:
        iface_config = {}

    ethernet_cfg = ensure_mapping(iface_config.get("ethernet"))

    available_set: set[str] = set()
    for iface_name, iface_data in ethernet_cfg.items():
        base_name = str(iface_name)
        if not base_name:
            continue
        normalized = (normalise_iface_name(base_name) or base_name).lower()
        if normalized not in assigned and base_name.lower() not in assigned:
            available_set.add(base_name)

        vif_container = ensure_mapping(iface_data).get("vif")
        vif_map = ensure_mapping(vif_container)
        for vlan_id in vif_map.keys():
            vif_name = f"{base_name}.{vlan_id}"
            vif_normalized = (normalise_iface_name(vif_name) or vif_name).lower()
            if vif_normalized not in assigned and vif_name.lower() not in assigned:
                available_set.add(vif_name)

    return sorted(available_set)


def build_firewall_seed_commands(name: str, seed_accept: bool) -> List[List[str]]:
    commands: List[List[str]] = [
        ["firewall", "ipv4", "name", name],
        ["firewall", "ipv4", "name", name, "default-action", "drop"],
    ]
    if seed_accept:
        commands.append(["firewall", "ipv4", "name", name, "rule", "10"])
        commands.append(["firewall", "ipv4", "name", name, "rule", "10", "action", "accept"])
    return commands

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Blueprint, current_app, jsonify, render_template, request, url_for

from app.auth import login_required
from app.core import mark_config_dirty
from app.modules.interfaces.device import configure_delete, configure_set
from app.modules.interfaces.zone import (
    build_zone_binding_commands,
    build_zone_definition_commands,
    build_zone_intra_firewall_commands,
    build_zone_membership_commands,
    build_zone_membership_delete,
    load_zone_config,
    map_zone_members,
    sanitise_zone_name,
    zone_pair_firewall_name,
)
from app.modules.interfaces.utils import normalise_iface_name

from app.modules.firewall.common import load_firewall_root
from app.modules.firewall.rules.utils import dedupe_commands, ensure_mapping
from app.modules.firewall.zone.utils import (
    build_firewall_seed_commands,
    build_zone_map,
    list_unassigned_interfaces,
)

zone_bp = Blueprint("firewall_zone", __name__, url_prefix="/firewall/zones")


def _sorted_zone_names(zone_config: Dict[str, Any]) -> List[str]:
    names = [sanitise_zone_name(name) for name in zone_config.keys()]
    return sorted({name for name in names if name})


def _load_dashboard_payload() -> Dict[str, Any]:
    zone_config = load_zone_config() or {}
    zone_membership = map_zone_members(zone_config)
    zone_names = _sorted_zone_names(zone_config)
    zone_map = build_zone_map()

    firewall_root = load_firewall_root()
    firewall_name_map = ensure_mapping(firewall_root.get("name"))
    firewall_names = {str(key) for key in firewall_name_map.keys()}

    zones_summary = []
    for original_name, members in zone_membership.items():
        sanitized = sanitise_zone_name(original_name)
        zones_summary.append({
            "name": sanitized,
            "display_name": original_name,
            "members": sorted(members),
            "member_count": len(members),
        })
    zones_summary.sort(key=lambda item: item["name"])

    matrix: List[Dict[str, Any]] = []
    for source in zone_names:
        row_cells: List[Dict[str, Any]] = []
        for destination in zone_names:
            rule_name = zone_pair_firewall_name(source, destination)
            exists = rule_name in firewall_names
            metadata = zone_map.get(rule_name, {})
            cell = {
                "type": "self" if source == destination else "pair",
                "source": source,
                "destination": destination,
                "firewall": rule_name if exists else None,
                "exists": exists,
                "zone_label": metadata.get("zone_label"),
                "link": url_for('firewall_rules.overview') + f"?name={rule_name}",
            }
            if source == destination:
                cell["label"] = "Intra-zone"
            row_cells.append(cell)
        matrix.append({
            "source": source,
            "cells": row_cells,
        })

    available_interfaces = list_unassigned_interfaces()

    summary_cards = {
        "total_zones": len(zones_summary),
        "total_firewall_sets": len(firewall_names),
        "unassigned_interfaces": len(available_interfaces),
    }

    display_lookup = {entry['name']: entry['display_name'] or entry['name'] for entry in zones_summary}

    return {
        "zones": zones_summary,
        "matrix": matrix,
        "zone_names": zone_names,
        "zone_display_map": display_lookup,
        "unassigned_interfaces": available_interfaces,
        "summary": summary_cards,
    }


@zone_bp.route("/")
@login_required
def dashboard():
    context = _load_dashboard_payload()
    context.update({"active": "firewall", "active_subnav": "zones"})
    return render_template("firewall/zones/index.html", **context)


@zone_bp.route("/api/overview")
@login_required
def api_overview():
    data = _load_dashboard_payload()
    return jsonify({"status": "ok", "data": data})


def _normalize_interface_candidate(candidate: str, available: List[str]) -> Optional[str]:
    if not candidate:
        return None
    lookup = {iface.lower(): iface for iface in available}
    normalised = normalise_iface_name(candidate) or candidate
    key = normalised.lower()
    return lookup.get(key)


@zone_bp.route("/api/create", methods=["POST"])
@login_required
def api_create_zone():
    payload = request.get_json() or {}
    raw_name = payload.get("zoneName") or payload.get("name") or payload.get("zone")
    sanitized = sanitise_zone_name(raw_name or "")
    if not sanitized:
        return jsonify({"status": "error", "message": "Zone name is required."}), 400

    zone_config = load_zone_config() or {}
    existing_zone_names = {
        sanitise_zone_name(zone_name): zone_name for zone_name in zone_config.keys()
    }
    if sanitized in existing_zone_names:
        return jsonify({"status": "error", "message": f"Zone '{sanitized}' already exists."}), 400

    available_interfaces = list_unassigned_interfaces()
    interface_candidate = _normalize_interface_candidate(payload.get("interface", ""), available_interfaces)
    if not interface_candidate:
        return jsonify({"status": "error", "message": "Select an available interface to assign."}), 400

    commands: List[List[str]] = []
    commands.extend(build_zone_definition_commands(sanitized, zone_config))

    firewall_root = load_firewall_root()
    name_map = ensure_mapping(firewall_root.get("name"))
    existing_firewalls = {str(key) for key in name_map.keys()}

    existing_zones = [zone for zone in _sorted_zone_names(zone_config) if zone != sanitized]

    def should_seed_accept(source: str, destination: str) -> bool:
        if source == sanitized and destination in {"LOCAL", "WAN"}:
            return True
        if source == "LOCAL" and destination == sanitized:
            return True
        return False

    self_firewall_name = zone_pair_firewall_name(sanitized, sanitized)
    if self_firewall_name not in existing_firewalls:
        commands.extend(build_firewall_seed_commands(self_firewall_name, True))
        existing_firewalls.add(self_firewall_name)
    commands.extend(build_zone_intra_firewall_commands(sanitized, self_firewall_name))

    for zone in existing_zones:
        forward_name = zone_pair_firewall_name(sanitized, zone)
        reverse_name = zone_pair_firewall_name(zone, sanitized)

        if forward_name not in existing_firewalls:
            commands.extend(build_firewall_seed_commands(forward_name, should_seed_accept(sanitized, zone)))
            existing_firewalls.add(forward_name)
        if reverse_name not in existing_firewalls:
            commands.extend(build_firewall_seed_commands(reverse_name, should_seed_accept(zone, sanitized)))
            existing_firewalls.add(reverse_name)

        commands.extend(build_zone_binding_commands(sanitized, zone, forward_name))
        commands.extend(build_zone_binding_commands(zone, sanitized, reverse_name))

    commands.extend(build_zone_membership_commands(sanitized, interface_candidate))

    deduped_commands = dedupe_commands(commands)
    if not deduped_commands:
        return jsonify({"status": "error", "message": "Unable to build configuration for new zone."}), 400

    response = configure_set(deduped_commands, error_context=f"create firewall zone {sanitized}")
    success, error_message = response
    if not success:
        return jsonify({"status": "error", "message": error_message or "Failed to create zone."}), 500

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    data = _load_dashboard_payload()
    return jsonify({"status": "ok", "data": data})


@zone_bp.route("/api/delete", methods=["POST"])
@login_required
def api_delete_zone():
    payload = request.get_json() or {}
    sanitized = sanitise_zone_name(payload.get("zone") or "")
    if not sanitized:
        return jsonify({"status": "error", "message": "Zone name is required."}), 400

    zone_config = load_zone_config() or {}
    if sanitized not in {sanitise_zone_name(name) for name in zone_config.keys()}:
        return jsonify({"status": "error", "message": f"Zone '{sanitized}' not found."}), 404

    zone_membership = map_zone_members(zone_config)
    members = sorted(zone_membership.get(sanitized, []))

    existing_zones = [zone for zone in _sorted_zone_names(zone_config) if zone != sanitized]
    commands: List[List[str]] = []

    for iface in members:
        commands.extend(build_zone_membership_delete(sanitized, iface))

    firewall_root = load_firewall_root()
    name_map = ensure_mapping(firewall_root.get("name"))
    existing_firewalls = {str(key) for key in name_map.keys()}

    self_firewall_name = zone_pair_firewall_name(sanitized, sanitized)
    if self_firewall_name in existing_firewalls:
        commands.append(["firewall", "ipv4", "name", self_firewall_name])
    commands.extend(build_zone_intra_firewall_commands(sanitized, self_firewall_name))

    for zone in existing_zones:
        forward_name = zone_pair_firewall_name(sanitized, zone)
        reverse_name = zone_pair_firewall_name(zone, sanitized)
        if forward_name in existing_firewalls:
            commands.append(["firewall", "ipv4", "name", forward_name])
        if reverse_name in existing_firewalls:
            commands.append(["firewall", "ipv4", "name", reverse_name])
        commands.append(["firewall", "zone", zone, "from", sanitized])

    commands.append(["firewall", "zone", sanitized])

    deduped_commands = dedupe_commands(commands)
    if deduped_commands:
        success, error_message = configure_delete(deduped_commands, error_context=f"delete firewall zone {sanitized}")
        if not success:
            return jsonify({"status": "error", "message": error_message or "Failed to delete zone."}), 500

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    data = _load_dashboard_payload()
    return jsonify({"status": "ok", "data": data})


@zone_bp.route("/api/membership", methods=["POST"])
@login_required
def api_update_membership():
    payload = request.get_json() or {}
    zone_name = sanitise_zone_name(payload.get("zone") or "")
    iface = payload.get("interface")
    action = (payload.get("action") or "").lower()
    if not zone_name or not iface or action not in {"add", "remove"}:
        return jsonify({"status": "error", "message": "Zone, interface, and action are required."}), 400

    commands: List[List[str]] = []
    if action == "add":
        candidate = _normalize_interface_candidate(iface, list_unassigned_interfaces())
        if not candidate:
            return jsonify({"status": "error", "message": "Interface not available for assignment."}), 400
        commands.extend(build_zone_membership_commands(zone_name, candidate))
    else:
        commands.extend(build_zone_membership_delete(zone_name, iface))

    if commands:
        success, error_message = configure_set(commands, error_context=f"update zone {zone_name} membership") if action == "add" else configure_delete(commands, error_context=f"update zone {zone_name} membership")
        if not success:
            return jsonify({"status": "error", "message": error_message or "Failed to update zone membership."}), 500

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    data = _load_dashboard_payload()
    return jsonify({"status": "ok", "data": data})

from __future__ import annotations

import copy

from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import Blueprint, current_app, jsonify, render_template, request

from app.modules.interfaces.device import configure_delete, configure_set, configure_multiple_op

from app.auth import login_required
from app.core import mark_config_dirty
from app.modules.firewall.common import load_firewall_root
from app.modules.firewall.zone.utils import build_zone_map
from .utils import (
    build_rule_delete_commands,
    build_rule_disable_paths,
    build_rule_set_commands,
    dedupe_commands,
    ensure_mapping,
    extract_rule_description,
    extract_rule_ports,
    flatten_value,
    next_rule_number,
    flatten_rule_config,
    split_port_list,
)

rules_bp = Blueprint("firewall_rules", __name__, url_prefix="/firewall/rules")


def _load_firewall_name(name: str) -> Dict[str, Any]:
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "ipv4", "name", name])
        result = getattr(response, "result", {}) or {}
        if isinstance(result, dict) and name in result:
            return ensure_mapping(result[name])
        return ensure_mapping(result)
    except Exception:
        return {}


def _parse_firewall_metadata(name: str, config: Dict[str, Any], zone_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    description = flatten_value(config.get("description"))
    default_action = flatten_value(config.get("default-action"))
    rule_map = ensure_mapping(config.get("rule"))
    rule_count = len(rule_map)
    disabled = "disable" in config
    zone_details = zone_map.get(name, {})
    return {
        "name": name,
        "description": description,
        "default_action": default_action or "accept",
        "rule_count": rule_count,
        "disabled": disabled,
        "source_zone": zone_details.get("source_zone"),
        "destination_zone": zone_details.get("destination_zone"),
        "zone_label": zone_details.get("zone_label"),
    }


def _parse_firewall_rules(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    rule_map = ensure_mapping(config.get("rule"))
    sorted_rules = sorted(rule_map.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0])

    for rule_number, rule_cfg in sorted_rules:
        rule_details = ensure_mapping(rule_cfg)
        src_addr, src_port = extract_rule_ports(ensure_mapping(rule_details.get("source")))
        dst_addr, dst_port = extract_rule_ports(ensure_mapping(rule_details.get("destination")))
        rule_entry = {
            "number": str(rule_number),
            "protocol": flatten_value(rule_details.get("protocol")) or "any",
            "source": src_addr or "any",
            "source_port": src_port or "",
            "destination": dst_addr or "any",
            "destination_port": dst_port or "",
            "action": flatten_value(rule_details.get("action")) or "",
            "description": extract_rule_description(rule_details),
            "disabled": "disable" in rule_details,
        }
        rules.append(rule_entry)

    return rules


def _collect_firewall_list(
    root_config: Dict[str, Any]
) -> Tuple[List[str], Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, str]]]]:
    name_map = ensure_mapping(root_config.get("name"))
    zone_map = build_zone_map()
    metadata: Dict[str, Dict[str, Any]] = {}

    for name, cfg in name_map.items():
        if not isinstance(cfg, dict):
            cfg = ensure_mapping(cfg)
        metadata[name] = _parse_firewall_metadata(name, cfg, zone_map)

    zone_groups: Dict[str, List[Dict[str, str]]] = {}
    for name, meta in metadata.items():
        source_zone = (meta.get("source_zone") or "").upper()
        destination_zone = (meta.get("destination_zone") or "").upper()
        if not source_zone:
            continue
        zone_groups.setdefault(source_zone, []).append({
            "name": name,
            "destination": destination_zone,
        })

    for zone_name, entries in zone_groups.items():
        entries.sort(key=lambda item: ((item.get("destination") or ""), item.get("name") or ""))

    firewalls = sorted(metadata.keys(), key=lambda item: item.lower())
    return firewalls, metadata, zone_groups


def _rule_exists(config: Dict[str, Any], rule_number: int) -> bool:
    rule_map = ensure_mapping(config.get("rule"))
    return str(rule_number) in rule_map


def _current_rule_config(config: Dict[str, Any], rule_number: int) -> Dict[str, Any]:
    rule_map = ensure_mapping(config.get("rule"))
    return ensure_mapping(rule_map.get(str(rule_number), {}))


def _response_payload(name: str):
    config = _load_firewall_name(name)
    if not config:
        return None
    zone_map = build_zone_map()
    return {
        "metadata": _parse_firewall_metadata(name, config, zone_map),
        "rules": _parse_firewall_rules(config),
    }


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    value_str = str(value).strip().lower()
    return value_str in {"true", "1", "yes", "on"}


def _error(message: str, status: int = 400):
    return jsonify({"status": "error", "message": message}), status


def _ports_present(payload: Dict[str, Any]) -> bool:
    return bool(split_port_list(payload.get("sourcePort")) or split_port_list(payload.get("destinationPort")))


def _validate_ports_protocol(payload: Dict[str, Any]) -> bool:
    protocol = (payload.get("protocol") or "").strip().lower()
    if not _ports_present(payload):
        return True
    return protocol in {"tcp", "udp", "tcp_udp"}


@rules_bp.route("/")
@login_required
def overview():
    root_config = load_firewall_root()
    firewall_names, metadata, zone_groups = _collect_firewall_list(root_config)

    zone_list = sorted(zone_groups.keys())
    initial_zone = zone_list[0] if zone_list else None
    initial_name: Optional[str] = None
    if initial_zone:
        initial_pairs: Sequence[Dict[str, str]] = zone_groups.get(initial_zone, [])
        if initial_pairs:
            initial_name = initial_pairs[0]["name"]
    if not initial_name and firewall_names:
        initial_name = firewall_names[0]

    initial_config = _load_firewall_name(initial_name) if initial_name else {}
    initial_metadata = metadata.get(initial_name, {}) if initial_name else {}

    context = {
        "firewall_names": firewall_names,
        "firewall_metadata": metadata,
        "firewall_zone_groups": zone_groups,
        "firewall_zone_list": zone_list,
        "initial_zone": initial_zone,
        "initial_name": initial_name,
        "initial_details": {
            "metadata": initial_metadata,
            "rules": _parse_firewall_rules(initial_config) if initial_name else [],
        },
        "active": "firewall",
        "active_subnav": "rules",
    }

    return render_template("firewall/rules/index.html", **context)


@rules_bp.route("/api/names/<path:name>")
@login_required
def firewall_name_details(name: str):
    config = _load_firewall_name(name)
    if not config:
        return jsonify({"status": "error", "message": f"Firewall '{name}' not found."}), 404

    zone_map = build_zone_map()
    payload = {
        "metadata": _parse_firewall_metadata(name, config, zone_map),
        "rules": _parse_firewall_rules(config),
    }
    return jsonify({"status": "ok", "data": payload})


def _log_commands(action: str, commands: List[List[str]]):
    if current_app and current_app.logger:
        current_app.logger.info("Firewall %s commands: %s", action, commands)


@rules_bp.route("/api/names/<path:name>/rules", methods=["POST"])
@login_required
def create_firewall_rule(name: str):
    payload = request.get_json() or {}
    config = _load_firewall_name(name)
    if not config:
        return _error(f"Firewall '{name}' not found.", 404)

    action = (payload.get("action") or "").strip()
    if not action:
        return _error("Action is required for a firewall rule.", 400)

    protocol = (payload.get("protocol") or "").strip().lower()
    if not protocol:
        protocol = "tcp_udp"
    payload["protocol"] = protocol

    if not _validate_ports_protocol(payload):
        return _error("Source/destination ports require protocol tcp, udp, or tcp_udp.", 400)

    rule_map = ensure_mapping(config.get("rule"))
    requested_number = payload.get("number")

    if requested_number is None or str(requested_number).strip() == "":
        rule_number = next_rule_number(config)
    else:
        try:
            rule_number = int(str(requested_number))
        except ValueError:
            return _error("Rule number must be an integer.", 400)
        if str(rule_number) in rule_map:
            return _error(f"Rule number {rule_number} already exists.", 400)

    commands = build_rule_set_commands(name, rule_number, payload)
    _log_commands(f"create rule {rule_number} in {name}", commands)
    success, error_message = configure_set(commands, error_context=f"create firewall rule {rule_number} in {name}")
    if not success:
        return _error(error_message or "Failed to create firewall rule.", 500)

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    refreshed = _response_payload(name)
    return jsonify({"status": "ok", "data": refreshed})


@rules_bp.route("/api/names/<path:name>/rules/<int:rule_number>", methods=["PUT"])
@login_required
def update_firewall_rule(name: str, rule_number: int):
    payload = request.get_json() or {}
    config = _load_firewall_name(name)
    if not config:
        return _error(f"Firewall '{name}' not found.", 404)

    if not _rule_exists(config, rule_number):
        return _error(f"Rule {rule_number} does not exist in firewall '{name}'.", 404)

    rule_map = ensure_mapping(config.get("rule"))
    existing_rule = ensure_mapping(rule_map.get(str(rule_number), {}))

    new_number_raw = payload.get("number")
    target_number = rule_number
    if new_number_raw is not None and str(new_number_raw).strip() != "":
        try:
            target_number = int(str(new_number_raw))
        except ValueError:
            return _error("Rule number must be an integer.", 400)
        if target_number != rule_number and str(target_number) in rule_map:
            return _error(f"Rule number {target_number} already exists.", 400)

    action = (payload.get("action") or "").strip()
    if not action:
        existing_action = flatten_value(existing_rule.get("action"))
        if not existing_action:
            return _error("Action is required for the rule.", 400)
        payload["action"] = existing_action

    existing_protocol = (flatten_value(existing_rule.get("protocol")) or "").strip().lower()
    protocol = (payload.get("protocol") or "").strip().lower()
    if not protocol:
        protocol = existing_protocol
    payload["protocol"] = protocol

    if not _validate_ports_protocol(payload):
        return _error("Source/destination ports require protocol tcp, udp, or tcp_udp.", 400)

    # Build operations list for batch API call
    delete_paths = build_rule_delete_commands(name, rule_number)
    set_commands = build_rule_set_commands(name, target_number, payload)

    operations = []
    # Add delete operations
    for path in delete_paths:
        operations.append({"op": "delete", "path": path})
    # Add set operations
    for path in set_commands:
        operations.append({"op": "set", "path": path})

    _log_commands(f"update rule {rule_number} -> {target_number} in {name}", operations)

    # Execute all operations in a single API call
    success, error_message = configure_multiple_op(operations, error_context=f"update firewall rule {rule_number} in {name}")
    if not success:
        return _error(error_message or "Failed to update firewall rule.", 500)

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    refreshed = _response_payload(name)
    return jsonify({"status": "ok", "data": refreshed})


@rules_bp.route("/api/names/<path:name>/rules/reorder", methods=["POST"])
@login_required
def reorder_firewall_rules(name: str):
    payload = request.get_json() or {}
    order = payload.get("order")
    if not isinstance(order, list) or not order:
        return _error("Order must be a non-empty list of rule numbers.", 400)

    order = [str(item) for item in order]

    config = _load_firewall_name(name)
    if not config:
        return _error(f"Firewall '{name}' not found.", 404)

    rule_map = ensure_mapping(config.get("rule"))
    if len(order) != len(rule_map):
        return _error("Order length does not match existing rules.", 400)

    existing_keys = list(rule_map.keys())
    if set(order) != set(existing_keys):
        return _error("Order list must include every existing rule exactly once.", 400)

    sorted_numbers = sorted(int(key) for key in existing_keys)
    target_numbers = [str(num) for num in sorted_numbers]

    if all(order[idx] == target_numbers[idx] for idx in range(len(order))):
        refreshed = _response_payload(name)
        return jsonify({"status": "ok", "data": refreshed})

    snapshots: Dict[str, Dict[str, Any]] = {}
    for key in existing_keys:
        snapshots[key] = copy.deepcopy(ensure_mapping(rule_map.get(key, {})))

    delete_paths = [["firewall", "ipv4", "name", name, "rule", key] for key in existing_keys]

    set_commands: List[List[str]] = []
    for idx, rule_id in enumerate(order):
        rule_cfg = ensure_mapping(snapshots.get(rule_id, {}))
        target_number = target_numbers[idx]
        set_commands.extend(flatten_rule_config(rule_cfg, name, target_number))

    # Build operations list for batch API call
    operations = []
    # Add delete operations
    for path in delete_paths:
        operations.append({"op": "delete", "path": path})
    # Add set operations
    for path in set_commands:
        operations.append({"op": "set", "path": path})

    _log_commands(f"reorder rules in {name}", operations)

    # Execute all operations in a single API call
    success, error_message = configure_multiple_op(operations, error_context=f"reorder firewall rules in {name}")
    if not success:
        # Attempt to restore original state
        restore_operations = []
        for rule_id, rule_cfg in snapshots.items():
            restore_commands = flatten_rule_config(ensure_mapping(rule_cfg), name, rule_id)
            for path in restore_commands:
                restore_operations.append({"op": "set", "path": path})
        if restore_operations:
            _log_commands(f"restore firewall rules in {name} after failed reorder", restore_operations)
            configure_multiple_op(restore_operations, error_context=f"restore firewall rules in {name}")
        return _error(error_message or "Failed to apply reordered firewall rules.", 500)

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    refreshed = _response_payload(name)
    return jsonify({"status": "ok", "data": refreshed})


def _compact_rule_numbers(name: str, start_number: Optional[int] = None):
    config = _load_firewall_name(name)
    rule_map = ensure_mapping(config.get("rule"))
    if not rule_map:
        return True, None

    sorted_rules = sorted(
        rule_map.items(),
        key=lambda item: int(item[0]) if str(item[0]).isdigit() else item[0],
    )

    if start_number is not None:
        base_number = max(1, start_number)
    else:
        try:
            base_number = int(sorted_rules[0][0])
        except ValueError:
            base_number = 1

    mapping = []
    changed = False
    for index, (rule_number, rule_cfg) in enumerate(sorted_rules):
        target_number = str(base_number + index)
        if target_number != str(rule_number):
            changed = True
        mapping.append((str(rule_number), target_number, ensure_mapping(rule_cfg)))

    if not changed:
        return True, None

    delete_paths = [["firewall", "ipv4", "name", name, "rule", original] for original, _, _ in mapping]
    set_commands: List[List[str]] = []
    for _, target, rule_cfg in mapping:
        set_commands.extend(flatten_rule_config(rule_cfg, name, target))

    _log_commands(f"delete rules prior to compact numbering in {name}", delete_paths)
    success, error_message = configure_delete(delete_paths, error_context=f"compact firewall rules in {name}")
    if not success:
        return False, error_message

    _log_commands(f"apply compact numbering in {name}", set_commands)
    success, error_message = configure_set(set_commands, error_context=f"compact firewall rules in {name}")
    if not success:
        restore_commands: List[List[str]] = []
        for original, _, rule_cfg in mapping:
            restore_commands.extend(flatten_rule_config(rule_cfg, name, original))
        if restore_commands:
            _log_commands(f"restore firewall rules in {name} after compact failure", restore_commands)
            configure_set(restore_commands, error_context=f"restore firewall rules in {name}")
        return False, error_message

    return True, None


@rules_bp.route("/api/names/<path:name>/rules/<int:rule_number>", methods=["DELETE"])
@login_required
def delete_firewall_rule(name: str, rule_number: int):
    config = _load_firewall_name(name)
    if not config:
        return _error(f"Firewall '{name}' not found.", 404)

    if not _rule_exists(config, rule_number):
        return _error(f"Rule {rule_number} does not exist in firewall '{name}'.", 404)

    rule_map = ensure_mapping(config.get("rule"))
    base_hint: Optional[int] = None
    if rule_map:
        try:
            base_hint = min(int(str(key)) for key in rule_map.keys())
        except ValueError:
            base_hint = None

    delete_paths = build_rule_delete_commands(name, rule_number)
    _log_commands(f"delete rule {rule_number} in {name}", delete_paths)
    success, error_message = configure_delete(delete_paths, error_context=f"delete firewall rule {rule_number} in {name}")
    if not success:
        return _error(error_message or "Failed to delete firewall rule.", 500)

    compact_success, compact_error = _compact_rule_numbers(name, start_number=base_hint)
    if not compact_success:
        return _error(compact_error or "Failed to resequence firewall rules after deletion.", 500)

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    refreshed = _response_payload(name)
    return jsonify({"status": "ok", "data": refreshed})


@rules_bp.route("/api/names/<path:name>/rules/<int:rule_number>/toggle", methods=["POST"])
@login_required
def toggle_firewall_rule(name: str, rule_number: int):
    payload = request.get_json() or {}
    disable_flag = _parse_bool(payload.get("disabled"), default=True)

    config = _load_firewall_name(name)
    if not config:
        return _error(f"Firewall '{name}' not found.", 404)

    rule_config = _current_rule_config(config, rule_number)
    if not rule_config:
        return _error(f"Rule {rule_number} does not exist in firewall '{name}'.", 404)

    currently_disabled = "disable" in rule_config
    if disable_flag == currently_disabled:
        refreshed = _response_payload(name)
        return jsonify({"status": "ok", "data": refreshed})

    set_paths, delete_paths = build_rule_disable_paths(name, rule_number, disable_flag)
    if disable_flag:
        _log_commands(f"disable rule {rule_number} in {name}", set_paths)
        success, error_message = configure_set(set_paths, error_context=f"disable firewall rule {rule_number} in {name}")
    else:
        if delete_paths:
            _log_commands(f"enable rule {rule_number} in {name}", delete_paths)
            success, error_message = configure_delete(delete_paths, error_context=f"enable firewall rule {rule_number} in {name}")
        else:
            success, error_message = True, None

    if not success:
        return _error(error_message or "Failed to toggle firewall rule state.", 500)

    # Mark configuration as dirty (unsaved changes)
    mark_config_dirty()

    refreshed = _response_payload(name)
    return jsonify({"status": "ok", "data": refreshed})

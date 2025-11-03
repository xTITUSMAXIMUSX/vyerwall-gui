import re
from typing import Dict, List, Tuple

from flask import current_app

from .device import configure_set, configure_delete
from .utils import extract_leaf_value

FirewallCommands = List[List[str]]

EXPECTED_STATE_POLICY = {
    "established": "accept",
    "invalid": "drop",
    "related": "accept",
}


def _sanitize_token(value: str, fallback: str) -> str:
    candidate = (value or "").strip().lower()
    candidate = re.sub(r"[^a-z0-9_-]+", "-", candidate)
    candidate = re.sub(r"-{2,}", "-", candidate).strip("-")
    if candidate:
        return candidate

    fallback = (fallback or "").strip().lower()
    fallback = re.sub(r"[^a-z0-9_-]+", "-", fallback)
    fallback = re.sub(r"-{2,}", "-", fallback).strip("-")
    return fallback or "interface"


def firewall_name_for_description(description: str, fallback_iface: str) -> str:
    fallback_token = _sanitize_token(fallback_iface, "interface")
    description_value = (description or "").strip()
    if description_value:
        name = re.sub(r"\s+", "-", description_value)
        name = re.sub(r"[^A-Za-z0-9_-]+", "", name)
        if name:
            return name
    return fallback_token


def _firewall_description_marker(fallback_iface: str) -> str:
    token = _sanitize_token(fallback_iface, "interface")
    return f"iface:{token}"


def _load_state_policy_config() -> Dict:
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "global-options"])
        result = getattr(response, "result", {}) or {}
    except Exception:
        result = {}

    return result if isinstance(result, dict) else {}


def _state_policy_entry(state_policy: Dict, key: str):
    if isinstance(state_policy, dict):
        return state_policy.get(key)
    if isinstance(state_policy, list):
        for item in state_policy:
            if isinstance(item, dict) and key in item:
                return item.get(key)
    return None


def _missing_state_policy_commands() -> FirewallCommands:
    config = _load_state_policy_config()
    state_policy = config.get("state-policy", {})

    commands: FirewallCommands = []
    for key, expected_action in EXPECTED_STATE_POLICY.items():
        entry = _state_policy_entry(state_policy, key)
        if isinstance(entry, dict):
            action_value = extract_leaf_value(entry.get("action"))
        else:
            action_value = extract_leaf_value(entry)

        if str(action_value).lower() == expected_action:
            continue

        commands.append(["firewall", "global-options", "state-policy", key, "action", expected_action])

    return commands


def _load_firewall_name_config() -> Dict:
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "ipv4", "name"])
        result = getattr(response, "result", {}) or {}
    except Exception:
        result = {}

    if isinstance(result, dict):
        return result

    if isinstance(result, list):
        merged: Dict = {}
        for item in result:
            if isinstance(item, dict):
                merged.update(item)
        return merged

    return {}


def prepare_firewall_setup(description: str, fallback_iface: str) -> Tuple[str, FirewallCommands]:
    firewall_name = firewall_name_for_description(description, fallback_iface)
    commands: FirewallCommands = []
    commands.extend(_missing_state_policy_commands())
    commands.append(["firewall", "ipv4", "name", firewall_name])
    commands.append(["firewall", "ipv4", "name", firewall_name, "default-action", "drop"])
    commands.append([
        "firewall",
        "ipv4",
        "name",
        firewall_name,
        "description",
        _firewall_description_marker(fallback_iface),
    ])
    return firewall_name, commands


def apply_firewall_setup(commands: FirewallCommands, error_context: str = "firewall setup"):
    return configure_set(commands, error_context=error_context)


def prepare_firewall_teardown(description: str, fallback_iface: str) -> Tuple[str, FirewallCommands]:
    firewall_name = firewall_name_for_description(description, fallback_iface)
    config = _load_firewall_name_config()
    target_marker = _firewall_description_marker(fallback_iface)

    commands: FirewallCommands = [["firewall", "ipv4", "name", firewall_name]]

    for name, details in config.items():
        descriptor = extract_leaf_value(details.get("description")) if isinstance(details, dict) else None
        if name == firewall_name or descriptor == target_marker:
            commands.append(["firewall", "ipv4", "name", name])

    deduped: FirewallCommands = []
    seen = set()
    for cmd in commands:
        tuple_cmd = tuple(cmd)
        if tuple_cmd in seen:
            continue
        seen.add(tuple_cmd)
        deduped.append(cmd)

    return firewall_name, deduped


def apply_firewall_teardown(commands: FirewallCommands, error_context: str = "firewall teardown"):
    return configure_delete(commands, error_context=error_context)

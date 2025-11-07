from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

DEFAULT_RULE_START = 100

def ensure_mapping(node: Any) -> Dict[str, Any]:
    """Convert VyOS nested structures into a simple dict."""
    if isinstance(node, dict):
        return node
    if isinstance(node, list):
        merged: Dict[str, Any] = {}
        for entry in node:
            if isinstance(entry, dict):
                merged.update(entry)
        return merged
    return {}


def flatten_value(node: Any) -> str:
    """Flatten nested values into a user-friendly string."""
    if node is None:
        return ""
    if isinstance(node, (str, int, float)):
        return str(node)
    if isinstance(node, list):
        return ", ".join(filter(None, (flatten_value(item) for item in node)))
    if isinstance(node, dict):
        parts: List[str] = []
        for key, value in node.items():
            flat = flatten_value(value)
            if not flat:
                continue
            if key in {"address", "port"} and not isinstance(value, dict):
                parts.append(flat)
            else:
                parts.append(f"{key}={flat}")
        return ", ".join(parts)
    return str(node)


def extract_rule_ports(block: Dict[str, Any]) -> Tuple[str, str]:
    """Return (address, port) strings for a source/destination block.

    Now also handles firewall groups with special formatting.
    Groups are returned with a prefix like: [group:address-group:GROUP_NAME]
    """
    if not isinstance(block, dict):
        return "", ""

    address = ""
    port = ""

    # Check for add-address-to-group (used by dynamic groups)
    add_to_group_block = block.get("add-address-to-group")
    if isinstance(add_to_group_block, dict):
        # This is for dynamic-group: extract the address-group name
        # Structure: {"source-address": {"address-group": "GROUP_NAME"}} or {"destination-address": {...}}
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Found add-address-to-group block: {add_to_group_block}")
        for key in ["source-address", "destination-address"]:
            addr_block = add_to_group_block.get(key)
            if isinstance(addr_block, dict):
                addr_group = addr_block.get("address-group")
                if addr_group:
                    group_name = flatten_value(addr_group)
                    address = f"[group:dynamic-group:{group_name}]"
                    logger.debug(f"Extracted dynamic-group address: {address}")
                    break

    # Check for regular address groups
    if not address:
        group_block = block.get("group")
        if isinstance(group_block, dict):
            # Check all address-related group types
            address_group_types = [
                "address-group",
                "network-group",
                "mac-group",
                "domain-group",
                "dynamic-group",
                "remote-group",
                "ipv6-address-group",
                "ipv6-network-group"
            ]

            for group_type in address_group_types:
                group_value = group_block.get(group_type)
                if group_value:
                    group_name = flatten_value(group_value)
                    address = f"[group:{group_type}:{group_name}]"
                    break

            if not address:
                # No address group found, try regular address
                address = flatten_value(block.get("address"))

            # Port groups
            port_group = group_block.get("port-group")
            if port_group:
                group_name = flatten_value(port_group)
                port = f"[group:port-group:{group_name}]"
            else:
                port_entry = block.get("port") or block.get("port-name")
                port = flatten_value(port_entry)
                if not port and isinstance(block.get("port"), dict):
                    port = flatten_value(block.get("port"))
        else:
            # No groups, use regular address/port extraction
            address = flatten_value(block.get("address"))
            port_entry = block.get("port") or block.get("port-name") or block.get("port-group")
            port = flatten_value(port_entry)
            if not port and isinstance(block.get("port"), dict):
                port = flatten_value(block.get("port"))

    return address, port


def extract_rule_description(rule_cfg: Dict[str, Any]) -> str:
    if not isinstance(rule_cfg, dict):
        return ""
    description = rule_cfg.get("description")
    if description is None:
        return ""
    if isinstance(description, dict):
        description = list(description.keys())[0] if description else ""
    return str(description) if description is not None else ""


def extract_rule_numbers(config: Dict[str, Any]) -> List[int]:
    rule_map = ensure_mapping(config.get("rule"))
    numbers: List[int] = []
    for key in rule_map.keys():
        try:
            numbers.append(int(str(key)))
        except ValueError:
            continue
    return numbers


def next_rule_number(config: Dict[str, Any], start: int = DEFAULT_RULE_START) -> int:
    numbers = extract_rule_numbers(config)
    if not numbers:
        return start
    return max(numbers) + 1


def split_port_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    items: List[str] = []
    for token in str(value).split(","):
        token = token.strip()
        if not token:
            continue
        token = token.strip("'\"")
        if token:
            items.append(token)
    return items


def _append_port_commands(commands: List[List[str]], base: List[str], side: str, tokens: List[str]):
    if not tokens:
        return
    commands.append(base + [side, "port", ",".join(tokens)])


def build_rule_set_commands(firewall_name: str, rule_number: int, payload: Dict[str, Any]) -> List[List[str]]:
    base = ["firewall", "ipv4", "name", firewall_name, "rule", str(rule_number)]
    commands: List[List[str]] = [base]

    action = (payload.get("action") or "").strip()
    if action:
        commands.append(base + ["action", action])

    protocol = (payload.get("protocol") or "").strip()
    if protocol:
        commands.append(base + ["protocol", protocol])

    description = (payload.get("description") or "").strip()
    if description:
        commands.append(base + ["description", description])

    # Handle source address (manual or group)
    if payload.get("sourceAddressType") == "group":
        src_group = (payload.get("sourceAddressGroup") or "").strip()
        if src_group:
            # Format: "address-group:GROUP_NAME" or "network-group:GROUP_NAME"
            if ":" in src_group:
                group_type, group_name = src_group.split(":", 1)
                # Special handling for dynamic-group
                if group_type == "dynamic-group":
                    commands.append(base + ["add-address-to-group", "source-address", "address-group", group_name])
                    # Add timeout if provided
                    timeout_value = payload.get("sourceAddressTimeout")
                    timeout_unit = payload.get("sourceAddressTimeoutUnit", "m")
                    if timeout_value:
                        timeout_str = f"{timeout_value}{timeout_unit}"
                        commands.append(base + ["add-address-to-group", "source-address", "timeout", timeout_str])
                else:
                    commands.append(base + ["source", "group", group_type, group_name])
    else:
        src_addr = (payload.get("sourceAddress") or "").strip()
        if src_addr:
            commands.append(base + ["source", "address", src_addr])

    # Handle source port (manual or group)
    if payload.get("sourcePortType") == "group":
        src_port_group = (payload.get("sourcePortGroup") or "").strip()
        if src_port_group:
            commands.append(base + ["source", "group", "port-group", src_port_group])
    else:
        src_tokens = split_port_list(payload.get("sourcePort"))
        if src_tokens:
            _append_port_commands(commands, base, "source", src_tokens)

    # Handle destination address (manual or group)
    if payload.get("destinationAddressType") == "group":
        dst_group = (payload.get("destinationAddressGroup") or "").strip()
        if dst_group:
            # Format: "address-group:GROUP_NAME" or "network-group:GROUP_NAME"
            if ":" in dst_group:
                group_type, group_name = dst_group.split(":", 1)
                # Special handling for dynamic-group
                if group_type == "dynamic-group":
                    commands.append(base + ["add-address-to-group", "destination-address", "address-group", group_name])
                    # Add timeout if provided
                    timeout_value = payload.get("destinationAddressTimeout")
                    timeout_unit = payload.get("destinationAddressTimeoutUnit", "m")
                    if timeout_value:
                        timeout_str = f"{timeout_value}{timeout_unit}"
                        commands.append(base + ["add-address-to-group", "destination-address", "timeout", timeout_str])
                else:
                    commands.append(base + ["destination", "group", group_type, group_name])
    else:
        dst_addr = (payload.get("destinationAddress") or "").strip()
        if dst_addr:
            commands.append(base + ["destination", "address", dst_addr])

    # Handle destination port (manual or group)
    if payload.get("destinationPortType") == "group":
        dst_port_group = (payload.get("destinationPortGroup") or "").strip()
        if dst_port_group:
            commands.append(base + ["destination", "group", "port-group", dst_port_group])
    else:
        dst_tokens = split_port_list(payload.get("destinationPort"))
        if dst_tokens:
            _append_port_commands(commands, base, "destination", dst_tokens)

    disabled = payload.get("disabled")
    if isinstance(disabled, str):
        disabled_flag = disabled.lower() in {"true", "1", "yes", "on"}
    else:
        disabled_flag = bool(disabled)

    if disabled_flag:
        commands.append(base + ["disable"])

    return commands


def build_rule_delete_commands(firewall_name: str, rule_number: int) -> List[List[str]]:
    return [["firewall", "ipv4", "name", firewall_name, "rule", str(rule_number)]]


def build_rule_disable_paths(firewall_name: str, rule_number: int, disable: bool) -> Tuple[List[List[str]], List[List[str]]]:
    base = ["firewall", "ipv4", "name", firewall_name, "rule", str(rule_number), "disable"]
    if disable:
        return ([base], [])
    return ([], [base])


def dedupe_commands(commands: List[List[str]]) -> List[List[str]]:
    deduped: List[List[str]] = []
    seen = set()
    for cmd in commands:
        key = tuple(cmd)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cmd)
    return deduped


def flatten_config_tree(node: Any, prefix: List[str]) -> List[List[str]]:
    commands: List[List[str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_str = str(key)
            if isinstance(value, dict):
                if value:
                    commands.extend(flatten_config_tree(value, prefix + [key_str]))
                else:
                    commands.append(prefix + [key_str])
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        commands.extend(flatten_config_tree(item, prefix + [key_str]))
                    else:
                        commands.append(prefix + [key_str, str(item)])
            elif value is None:
                commands.append(prefix + [key_str])
            else:
                commands.append(prefix + [key_str, str(value)])
    elif isinstance(node, list):
        for item in node:
            commands.extend(flatten_config_tree(item, prefix))
    elif node is not None:
        commands.append(prefix + [str(node)])
    return commands


def flatten_rule_config(rule_cfg: Dict[str, Any], firewall_name: str, rule_number: str) -> List[List[str]]:
    base_path = ["firewall", "ipv4", "name", firewall_name, "rule", str(rule_number)]
    commands: List[List[str]] = [base_path]
    commands.extend(flatten_config_tree(rule_cfg, base_path))
    return dedupe_commands(commands)

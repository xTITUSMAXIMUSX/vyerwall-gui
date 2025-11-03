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
    """Return (address, port) strings for a source/destination block."""
    if not isinstance(block, dict):
        return "", ""

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

    src_addr = (payload.get("sourceAddress") or "").strip()
    if src_addr:
        commands.append(base + ["source", "address", src_addr])

    src_tokens = split_port_list(payload.get("sourcePort"))
    if src_tokens:
        _append_port_commands(commands, base, "source", src_tokens)

    dst_addr = (payload.get("destinationAddress") or "").strip()
    if dst_addr:
        commands.append(base + ["destination", "address", dst_addr])

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

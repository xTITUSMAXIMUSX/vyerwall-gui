import ipaddress
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

CIDR_PATTERN = re.compile(
    r'^(?P<oct1>\d{1,3})\.(?P<oct2>\d{1,3})\.(?P<oct3>\d{1,3})\.(?P<oct4>\d{1,3})/(?P<prefix>\d{1,2})$'
)


ConfigPath = Sequence[str]
CommandList = List[List[str]]


def extract_configured_interfaces(config_result: Any) -> set[str]:
    """Return a set of configured interface names without parent suffix (e.g. eth1.10)."""
    configured: set[str] = set()
    if not isinstance(config_result, dict):
        return configured

    ethernet_cfg = config_result.get("ethernet", {})
    if not isinstance(ethernet_cfg, dict):
        return configured

    for iface_name, iface_cfg in ethernet_cfg.items():
        configured.add(iface_name)

        if isinstance(iface_cfg, dict):
            vif_cfg = iface_cfg.get("vif", {})
            if isinstance(vif_cfg, dict):
                for vlan_id in vif_cfg.keys():
                    configured.add(f"{iface_name}.{vlan_id}")

    return configured


def extract_address_value(address_entry: Any) -> Optional[str]:
    """Normalise address config values to a single string."""
    if not address_entry:
        return None

    if isinstance(address_entry, str):
        return address_entry.strip()

    if isinstance(address_entry, list):
        return extract_address_value(address_entry[0]) if address_entry else None

    if isinstance(address_entry, dict):
        keys = list(address_entry.keys())
        if keys:
            first_key = keys[0]
            value = address_entry[first_key]
            if not value:
                return first_key
            if isinstance(value, dict):
                inner_keys = list(value.keys())
                if inner_keys:
                    return inner_keys[0]
            return first_key

    return None


def flatten_interface_config(config_result: Any) -> Dict[str, Dict[str, Any]]:
    """Flatten VyOS interface configuration for quick lookups."""
    flat: Dict[str, Dict[str, Any]] = {}
    if not isinstance(config_result, dict):
        return flat

    ethernet_cfg = config_result.get("ethernet", {})
    if not isinstance(ethernet_cfg, dict):
        return flat

    for iface_name, iface_cfg in ethernet_cfg.items():
        if not isinstance(iface_cfg, dict):
            iface_cfg = {}

        flat[iface_name] = {
            "address": extract_address_value(iface_cfg.get("address")),
            "description": iface_cfg.get("description"),
        }

        vif_cfg = iface_cfg.get("vif", {})
        if isinstance(vif_cfg, dict):
            for vlan_id, vlan_data in vif_cfg.items():
                if not isinstance(vlan_data, dict):
                    vlan_data = {}

                flat[f"{iface_name}.{vlan_id}"] = {
                    "address": extract_address_value(vlan_data.get("address")),
                    "description": vlan_data.get("description"),
                }

    return flat


def normalise_shared_name(name: Optional[str], fallback: str) -> str:
    candidate = (name or '').strip() or fallback
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', candidate)
    return safe or fallback


def extract_leaf_value(node: Any) -> Optional[str]:
    """Return the first meaningful value from nested config nodes."""
    if node is None:
        return None

    if isinstance(node, str):
        return node

    if isinstance(node, (int, float)):
        return str(node)

    if isinstance(node, list):
        for item in node:
            value = extract_leaf_value(item)
            if value is not None:
                return value
        return None

    if isinstance(node, dict):
        if not node:
            return None
        if len(node) == 1:
            key, value = next(iter(node.items()))
            nested = extract_leaf_value(value)
            return nested if nested is not None else str(key)
        return None

    return str(node)


def normalise_rule_map(rule_container: Any) -> Dict[int, Dict[str, Any]]:
    """Convert VyOS rule containers into a dict keyed by integer rule numbers."""
    rule_map: Dict[int, Dict[str, Any]] = {}
    items: Iterable[Tuple[Any, Any]] = ()

    if isinstance(rule_container, dict):
        items = rule_container.items()
    elif isinstance(rule_container, list):
        collected: List[Tuple[Any, Any]] = []
        for entry in rule_container:
            if isinstance(entry, dict):
                collected.extend(entry.items())
        items = collected

    for raw_rule, contents in items:
        try:
            rule_number = int(raw_rule)
        except (TypeError, ValueError):
            continue
        rule_map[rule_number] = contents if isinstance(contents, dict) else {}

    return dict(sorted(rule_map.items()))


def flatten_config_tree(node: Any, prefix: Optional[List[str]] = None) -> CommandList:
    """Flatten a config dictionary into CLI command paths."""
    if prefix is None:
        prefix = []

    commands: CommandList = []

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
        return commands

    if isinstance(node, list):
        for item in node:
            commands.extend(flatten_config_tree(item, prefix))
        return commands

    return commands


def load_cidr_network(address: Optional[str]) -> Optional[str]:
    """Convert an interface CIDR address to its network string."""
    if not address or isinstance(address, str) and address.lower() == "dhcp":
        return None
    try:
        return str(ipaddress.ip_interface(address).network)
    except (ValueError, TypeError):
        return None


def normalise_iface_name(iface_name: Optional[str]) -> Optional[str]:
    """Strip any parent suffix (e.g. eth1.10@eth1 -> eth1.10)."""
    return iface_name.split("@")[0] if iface_name else iface_name


def is_valid_cidr(address: Optional[str]) -> bool:
    """Validate IPv4 CIDR notation."""
    if not address:
        return False

    match = CIDR_PATTERN.match(address)
    if not match:
        return False

    octets = [
        int(match.group("oct1")),
        int(match.group("oct2")),
        int(match.group("oct3")),
        int(match.group("oct4")),
    ]
    prefix = int(match.group("prefix"))

    if not (0 <= prefix <= 32):
        return False

    return all(0 <= octet <= 255 for octet in octets)

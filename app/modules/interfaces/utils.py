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


def is_valid_network_prefix(address: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that an IP/CIDR forms a valid network prefix by checking if the
    user-provided IP creates a valid network for the given prefix length.

    Returns (is_valid, error_message).

    This checks if the resulting network would be valid in VyOS/networking terms.
    For example:
    - 10.5.4.1/23 -> Valid (creates network 10.5.4.0/23, which is valid)
    - 10.5.5.1/23 -> Invalid (would create network 10.5.4.0/23 per Python, but the IP
                             suggests 10.5.5.0/23 which is invalid for /23)
    - 10.6.6.1/23 -> Valid (creates network 10.6.6.0/23, which is valid)
    """
    if not address:
        return False, "No address provided"

    # First check basic CIDR format
    if not is_valid_cidr(address):
        return False, "Invalid CIDR notation"

    try:
        # Parse the input to extract IP and prefix
        parts = address.split('/')
        if len(parts) != 2:
            return False, "Invalid CIDR format"

        ip_str = parts[0]
        prefix_len = int(parts[1])

        # Parse the IP address
        ip_obj = ipaddress.IPv4Address(ip_str)

        # Create network from this IP - this will auto-normalize to the correct network
        iface = ipaddress.ip_interface(address)
        calculated_network = iface.network

        # The key check: Calculate what network the user's IP octets would suggest
        # For 10.5.5.1/23, the third octet is 5, which suggests 10.5.5.0/23
        # But we need to check if 10.5.5.0/23 is a valid /23 network

        # Get the "suggested" network by zeroing host bits of the user's IP
        ip_int = int(ip_obj)

        # Create a suggested network address by taking the user's IP up to the network boundary
        # For a /23, we zero out the last 9 bits (32 - 23 = 9)
        # But we check against the user's perception of the network

        # Simple approach: check if the third octet (for /16-/24 masks) is compatible
        # For /23: third octet must be even (divisible by 2)
        # For /22: third octet must be divisible by 4
        # For /21: third octet must be divisible by 8
        # etc.

        octets = [int(x) for x in ip_str.split('.')]

        if prefix_len >= 24:
            # /24 or smaller - any IP is fine, just validating the network exists
            pass
        elif prefix_len >= 16:
            # /16 to /23 - need to check third octet alignment
            bits_in_third_octet = max(0, 24 - prefix_len)
            if bits_in_third_octet > 0:
                modulus = 2 ** bits_in_third_octet
                if octets[2] % modulus != 0:
                    # The third octet doesn't align
                    correct_third_octet = (octets[2] // modulus) * modulus
                    suggested_network = f"{octets[0]}.{octets[1]}.{correct_third_octet}.0/{prefix_len}"
                    return False, f"{address} is not a valid network prefix. For /{prefix_len}, the third octet must be divisible by {modulus}. Did you mean {suggested_network}?"
        elif prefix_len >= 8:
            # /8 to /15 - need to check second octet alignment
            bits_in_second_octet = max(0, 16 - prefix_len)
            if bits_in_second_octet > 0:
                modulus = 2 ** bits_in_second_octet
                if octets[1] % modulus != 0:
                    correct_second_octet = (octets[1] // modulus) * modulus
                    suggested_network = f"{octets[0]}.{correct_second_octet}.0.0/{prefix_len}"
                    return False, f"{address} is not a valid network prefix. For /{prefix_len}, the second octet must be divisible by {modulus}. Did you mean {suggested_network}?"
        else:
            # /1 to /7 - need to check first octet alignment
            modulus = 2 ** (8 - prefix_len)
            if octets[0] % modulus != 0:
                correct_first_octet = (octets[0] // modulus) * modulus
                suggested_network = f"{correct_first_octet}.0.0.0/{prefix_len}"
                return False, f"{address} is not a valid network prefix. For /{prefix_len}, the first octet must be divisible by {modulus}. Did you mean {suggested_network}?"

        return True, None

    except (ValueError, TypeError, IndexError) as e:
        return False, f"Invalid IP address format: {str(e)}"

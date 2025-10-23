import ipaddress
from typing import Dict, Iterable, List, Optional, Tuple

from flask import current_app

from .util import load_cidr_network, normalise_shared_name

Command = List[str]
CommandList = List[Command]


def build_dhcp_paths(shared_name: str, interface_ip_cidr: str, subnet_id: int, lease_seconds: str = "86400") -> CommandList:
    """Create DHCP server configuration paths for a given interface CIDR."""
    if not interface_ip_cidr:
        return []

    try:
        iface = ipaddress.ip_interface(interface_ip_cidr)
    except ValueError:
        return []

    network = iface.network
    # Determine range start (network + 20) but ensure within network hosts
    host_offset = 20
    max_host_offset = max(1, network.num_addresses - 2)
    start_offset = min(host_offset, max_host_offset)
    range_start_ip = network.network_address + start_offset
    range_stop_ip = network.broadcast_address - 1 if network.num_addresses > 2 else network.network_address

    shared_name = normalise_shared_name(shared_name, iface.ip.exploded)
    subnet_str = str(network)
    router_ip = iface.ip.exploded
    subnet_id = str(subnet_id) if subnet_id is not None else "0"

    dhcp_paths: CommandList = [
        ["service", "dhcp-server", "shared-network-name", shared_name],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "option", "default-router", router_ip],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "option", "name-server", router_ip],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "option", "domain-name", "vyos.net"],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "lease", str(lease_seconds)],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "range", "0", "start", str(range_start_ip)],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "range", "0", "stop", str(range_stop_ip)],
        ["service", "dhcp-server", "shared-network-name", shared_name, "subnet", subnet_str, "subnet-id", subnet_id],
    ]

    return dhcp_paths


def load_dhcp_config() -> Dict:
    try:
        dhcp_config = current_app.device.retrieve_show_config(path=["service", "dhcp-server"])
        config = getattr(dhcp_config, "result", {}) or {}
    except Exception:
        config = {}

    return config if isinstance(config, dict) else {}


def get_next_subnet_id(dhcp_config: Optional[Dict] = None) -> int:
    """Return the lowest available DHCP subnet-id."""
    config = dhcp_config if dhcp_config is not None else load_dhcp_config()

    existing_ids = set()
    shared_networks = config.get("shared-network-name", {})
    if isinstance(shared_networks, dict):
        network_iterable: Iterable = shared_networks.values()
    elif isinstance(shared_networks, list):
        network_iterable = shared_networks
    else:
        network_iterable = []

    for network_cfg in network_iterable:
        if not isinstance(network_cfg, dict):
            continue

        subnets = network_cfg.get("subnet", {})
        if isinstance(subnets, dict):
            subnet_iterable = subnets.values()
        elif isinstance(subnets, list):
            subnet_iterable = subnets
        else:
            subnet_iterable = []

        for subnet_cfg in subnet_iterable:
            if not isinstance(subnet_cfg, dict):
                continue

            subnet_id = subnet_cfg.get("subnet-id")
            if subnet_id is None:
                continue
            if isinstance(subnet_id, dict):
                keys = list(subnet_id.keys())
                if keys:
                    try:
                        existing_ids.add(int(keys[0]))
                    except ValueError:
                        continue
            else:
                try:
                    existing_ids.add(int(subnet_id))
                except (TypeError, ValueError):
                    continue

    candidate = 1
    while candidate in existing_ids:
        candidate += 1

    return candidate


def has_active_dhcp_scope(dhcp_config: Optional[Dict] = None) -> bool:
    """Return True if at least one DHCP shared-network is enabled."""
    config = dhcp_config if dhcp_config is not None else load_dhcp_config()

    shared_networks = config.get("shared-network-name", {})
    if isinstance(shared_networks, dict):
        network_iterable = shared_networks.values()
    elif isinstance(shared_networks, list):
        network_iterable = shared_networks
    else:
        return False

    for network_cfg in network_iterable:
        if not isinstance(network_cfg, dict):
            continue

        if network_cfg.get("disable") is not None:
            continue

        subnets = network_cfg.get("subnet", {})
        if isinstance(subnets, dict):
            subnet_iterable = subnets.values()
        elif isinstance(subnets, list):
            subnet_iterable = subnets
        else:
            subnet_iterable = []

        for subnet_cfg in subnet_iterable:
            if not isinstance(subnet_cfg, dict):
                continue
            if subnet_cfg.get("disable") is not None:
                continue
            return True

    return False


def dns_cache_commands() -> CommandList:
    """Ensure DNS forwarding cache-size is set to 0."""
    try:
        dns_config = current_app.device.retrieve_show_config(path=["service", "dns"])
        result = getattr(dns_config, "result", {}) or {}
    except Exception:
        result = {}

    forwarding = result.get("forwarding", {})
    existing_cache = None
    if isinstance(forwarding, dict):
        existing_cache = forwarding.get("cache-size")
        if isinstance(existing_cache, dict):
            keys = list(existing_cache.keys())
            existing_cache = keys[0] if keys else None

    if str(existing_cache) == "0":
        return []

    return [["service", "dns", "forwarding", "cache-size", "0"]]


def build_dns_paths(interface_ip_cidr: Optional[str]) -> Tuple[CommandList, Optional[str], Optional[str]]:
    """Return DNS forwarding commands and metadata for a given interface CIDR."""
    if not interface_ip_cidr or interface_ip_cidr.lower() == "dhcp":
        return [], None, None

    try:
        iface = ipaddress.ip_interface(interface_ip_cidr)
    except ValueError:
        return [], None, None

    listen_ip = iface.ip.exploded
    network_str = str(iface.network)

    commands: CommandList = [
        ["service", "dns", "forwarding", "listen-address", listen_ip],
        ["service", "dns", "forwarding", "allow-from", network_str],
    ]

    return commands, listen_ip, network_str

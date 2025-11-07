"""
Utility functions for firewall group management.
"""
import re
from typing import Dict, List, Any, Optional, Tuple


# Group type configuration
GROUP_TYPES = {
    'address-group': {
        'display_name': 'Address Group',
        'icon': 'location_on',
        'member_key': 'address',
        'member_label': 'Address',
        'placeholder': 'e.g., 10.0.0.1 or 10.0.0.1-10.0.0.10',
        'description': 'Group IPv4/IPv6 addresses and ranges'
    },
    'domain-group': {
        'display_name': 'Domain Group',
        'icon': 'language',
        'member_key': 'address',
        'member_label': 'Domain',
        'placeholder': 'e.g., example.com',
        'description': 'Group domain names'
    },
    'interface-group': {
        'display_name': 'Interface Group',
        'icon': 'settings_ethernet',
        'member_key': 'interface',
        'member_label': 'Interface',
        'placeholder': 'e.g., eth0, eth1.5',
        'description': 'Group network interfaces'
    },
    'mac-group': {
        'display_name': 'MAC Group',
        'icon': 'router',
        'member_key': 'mac-address',
        'member_label': 'MAC Address',
        'placeholder': 'e.g., 00:11:22:33:44:55',
        'description': 'Group MAC addresses'
    },
    'network-group': {
        'display_name': 'Network Group',
        'icon': 'cloud',
        'member_key': 'network',
        'member_label': 'Network',
        'placeholder': 'e.g., 192.168.1.0/24',
        'description': 'Group network subnets (CIDR notation)'
    },
    'port-group': {
        'display_name': 'Port Group',
        'icon': 'power',
        'member_key': 'port',
        'member_label': 'Port',
        'placeholder': 'e.g., 80, 443, 8080-8090, http',
        'description': 'Group ports, port ranges, or service names'
    },
    'remote-group': {
        'display_name': 'Remote Group',
        'icon': 'cloud_download',
        'member_key': 'url',
        'member_label': 'URL',
        'placeholder': 'e.g., https://example.com/list.txt',
        'description': 'Dynamically update group from remote URL'
    },
    'dynamic-group': {
        'display_name': 'Dynamic Group',
        'icon': 'dynamic_feed',
        'member_key': 'address',
        'member_label': 'Address',
        'placeholder': 'Dynamically populated from firewall rules',
        'description': 'Group addresses dynamically added by firewall rules'
    },
    'ipv6-address-group': {
        'display_name': 'IPv6 Address Group',
        'icon': 'language',
        'member_key': 'address',
        'member_label': 'IPv6 Address',
        'placeholder': 'e.g., 2001:db8::1 or 2001:db8::1-2001:db8::10',
        'description': 'Group IPv6 addresses and ranges'
    },
    'ipv6-network-group': {
        'display_name': 'IPv6 Network Group',
        'icon': 'cloud',
        'member_key': 'network',
        'member_label': 'IPv6 Network',
        'placeholder': 'e.g., 2001:db8::/32',
        'description': 'Group IPv6 network subnets (CIDR notation)'
    }
}


def parse_firewall_groups(config_data: Dict) -> Dict[str, List[Dict]]:
    """
    Parse firewall group configuration into structured format.

    Args:
        config_data: Raw config data from VyOS

    Returns:
        Dictionary keyed by group type with lists of group objects
    """
    groups_by_type = {}

    for group_type in GROUP_TYPES.keys():
        groups_by_type[group_type] = []

        # Get groups of this type
        type_config = config_data.get(group_type, {})

        if not isinstance(type_config, dict):
            continue

        for group_name, group_data in type_config.items():
            if not isinstance(group_data, dict):
                continue

            # Get the member key for this group type
            member_key = GROUP_TYPES[group_type]['member_key']

            # Extract members
            members = []
            member_data = group_data.get(member_key, {})

            if isinstance(member_data, dict):
                # Members are keys in a dict
                members = list(member_data.keys())
            elif isinstance(member_data, list):
                # Members are in a list
                members = member_data
            elif isinstance(member_data, str):
                # Single member
                members = [member_data]

            # Extract description
            description = group_data.get('description', '')
            if isinstance(description, dict):
                description = ''

            groups_by_type[group_type].append({
                'name': group_name,
                'description': description,
                'members': members,
                'member_count': len(members),
                'type': group_type
            })

    return groups_by_type


def get_all_groups_summary(config_data: Dict) -> List[Dict]:
    """
    Get a summary of all groups across all types.

    Args:
        config_data: Raw config data from VyOS

    Returns:
        List of all groups with summary information
    """
    all_groups = []
    groups_by_type = parse_firewall_groups(config_data)

    for group_type, groups in groups_by_type.items():
        for group in groups:
            all_groups.append({
                **group,
                'type_display': GROUP_TYPES[group_type]['display_name'],
                'icon': GROUP_TYPES[group_type]['icon']
            })

    return sorted(all_groups, key=lambda x: (x['type'], x['name']))


def build_group_set_commands(group_type: str, group_name: str, members: List[str], description: str = '') -> List[List[str]]:
    """
    Build VyOS set commands for creating/updating a firewall group.

    Args:
        group_type: Type of group (e.g., 'address-group')
        group_name: Name of the group
        members: List of member values
        description: Optional description

    Returns:
        List of command paths for configure_multiple_op
    """
    commands = []
    base_path = ['firewall', 'group', group_type, group_name]
    member_key = GROUP_TYPES[group_type]['member_key']

    # Add description if provided
    if description:
        commands.append(base_path + ['description', description])

    # Add members
    for member in members:
        if member.strip():
            commands.append(base_path + [member_key, member.strip()])

    return commands


def build_group_delete_commands(group_type: str, group_name: str) -> List[List[str]]:
    """
    Build VyOS delete commands for removing a firewall group.

    Args:
        group_type: Type of group
        group_name: Name of the group

    Returns:
        List of command paths for configure_multiple_op
    """
    return [['firewall', 'group', group_type, group_name]]


def validate_group_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a firewall group name.

    Args:
        name: Group name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Group name is required"

    if len(name) > 63:
        return False, "Group name must be 63 characters or less"

    # VyOS group names must start with letter, contain only alphanumeric, dash, underscore
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        return False, "Group name must start with a letter and contain only letters, numbers, dashes, and underscores"

    return True, None


def validate_address(address: str) -> Tuple[bool, Optional[str]]:
    """Validate an IP address or address range."""
    if not address:
        return False, "Address is required"

    # Check for range (e.g., 10.0.0.1-10.0.0.10)
    if '-' in address:
        parts = address.split('-')
        if len(parts) != 2:
            return False, "Invalid address range format"
        # Basic validation - VyOS will handle detailed validation
        return True, None

    # Basic IP validation pattern (IPv4 or IPv6)
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'

    if re.match(ipv4_pattern, address) or re.match(ipv6_pattern, address):
        return True, None

    return False, "Invalid IP address format"


def validate_domain(domain: str) -> Tuple[bool, Optional[str]]:
    """Validate a domain name."""
    if not domain:
        return False, "Domain is required"

    # Basic domain validation
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,}$'

    if re.match(domain_pattern, domain):
        return True, None

    return False, "Invalid domain format"


def validate_network(network: str) -> Tuple[bool, Optional[str]]:
    """Validate a network in CIDR notation."""
    if not network:
        return False, "Network is required"

    # Check CIDR format
    if '/' not in network:
        return False, "Network must be in CIDR notation (e.g., 192.168.1.0/24)"

    parts = network.split('/')
    if len(parts) != 2:
        return False, "Invalid CIDR format"

    # Basic validation - VyOS will handle detailed validation
    return True, None


def validate_mac_address(mac: str) -> Tuple[bool, Optional[str]]:
    """Validate a MAC address."""
    if not mac:
        return False, "MAC address is required"

    # MAC address patterns (various formats)
    patterns = [
        r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$',  # 00:11:22:33:44:55
        r'^([0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}$',  # 00-11-22-33-44-55
        r'^[0-9A-Fa-f]{12}$'                       # 001122334455
    ]

    for pattern in patterns:
        if re.match(pattern, mac):
            return True, None

    return False, "Invalid MAC address format"


def validate_port(port: str) -> Tuple[bool, Optional[str]]:
    """Validate a port number, range, or service name."""
    if not port:
        return False, "Port is required"

    # Check for port range (e.g., 8080-8090)
    if '-' in port:
        parts = port.split('-')
        if len(parts) != 2:
            return False, "Invalid port range format"
        # VyOS will validate the actual range
        return True, None

    # Check if it's a number
    if port.isdigit():
        port_num = int(port)
        if 1 <= port_num <= 65535:
            return True, None
        return False, "Port must be between 1 and 65535"

    # Otherwise assume it's a service name (http, https, etc.)
    if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', port):
        return True, None

    return False, "Invalid port format"


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate a URL."""
    if not url:
        return False, "URL is required"

    # Basic URL validation
    url_pattern = r'^https?://[^\s]+$'

    if re.match(url_pattern, url):
        return True, None

    return False, "Invalid URL format (must start with http:// or https://)"


def validate_member(group_type: str, member: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a group member based on group type.

    Args:
        group_type: Type of group
        member: Member value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    validators = {
        'address-group': validate_address,
        'domain-group': validate_domain,
        'network-group': validate_network,
        'mac-group': validate_mac_address,
        'port-group': validate_port,
        'remote-group': validate_url,
        'interface-group': lambda x: (True, None)  # Interface names are flexible
    }

    validator = validators.get(group_type)
    if validator:
        return validator(member)

    return True, None

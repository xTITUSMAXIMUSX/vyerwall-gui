"""
Utility functions for static routes management.
"""
from typing import List, Dict, Optional


def parse_static_routes(config_data: dict) -> List[Dict]:
    """
    Parse VyOS static route configuration into a structured list.

    Args:
        config_data: Dictionary from retrieve_show_config('protocols static')

    Returns:
        List of route dictionaries with 'destination', 'next_hop', and 'description' keys
    """
    routes = []

    if not config_data or 'route' not in config_data:
        return routes

    route_config = config_data['route']

    for destination, route_data in route_config.items():
        if isinstance(route_data, dict) and 'next-hop' in route_data:
            next_hops = route_data['next-hop']

            # Extract description at route level (not under next-hop)
            route_description = route_data.get('description', '') if isinstance(route_data, dict) else ''

            # Handle multiple next-hops for the same destination
            for next_hop, hop_data in next_hops.items():
                route = {
                    'destination': destination,
                    'next_hop': next_hop,
                    'description': route_description
                }

                routes.append(route)

    return routes


def build_route_set_commands(destination: str, next_hop: str, description: Optional[str] = None) -> List[List[str]]:
    """
    Build VyOS command paths for setting a static route.

    Args:
        destination: Route destination in CIDR notation (e.g., '0.0.0.0/0')
        next_hop: Next-hop IP address
        description: Optional route description

    Returns:
        List of command paths for configure_set
    """
    commands = []

    # Base route command with next-hop
    next_hop_path = ['protocols', 'static', 'route', destination, 'next-hop', next_hop]
    commands.append(next_hop_path)

    # Add description at route level (not under next-hop)
    if description:
        desc_path = ['protocols', 'static', 'route', destination, 'description', description]
        commands.append(desc_path)

    return commands


def build_route_delete_commands(destination: str, next_hop: str) -> List[List[str]]:
    """
    Build VyOS command paths for deleting a static route.

    Args:
        destination: Route destination in CIDR notation
        next_hop: Next-hop IP address

    Returns:
        List of command paths for configure_delete
    """
    # Delete the entire route (this will remove all next-hops and descriptions for this destination)
    # If there are multiple next-hops for the same destination, we only delete the specific next-hop
    return [['protocols', 'static', 'route', destination, 'next-hop', next_hop]]


def validate_route(destination: str, next_hop: str) -> tuple[bool, Optional[str]]:
    """
    Validate static route parameters.

    Args:
        destination: Route destination in CIDR notation
        next_hop: Next-hop IP address

    Returns:
        Tuple of (is_valid, error_message)
    """
    import re

    # Validate destination CIDR format
    cidr_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
    if not re.match(cidr_pattern, destination):
        return False, "Invalid destination format. Use CIDR notation (e.g., 0.0.0.0/0)"

    # Validate IP address octets in destination
    ip_part = destination.split('/')[0]
    octets = ip_part.split('.')
    for octet in octets:
        if not 0 <= int(octet) <= 255:
            return False, "Invalid IP address in destination"

    # Validate prefix length
    prefix = int(destination.split('/')[1])
    if not 0 <= prefix <= 32:
        return False, "Invalid prefix length. Must be between 0 and 32"

    # Validate next-hop IP format
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, next_hop):
        return False, "Invalid next-hop IP address format"

    # Validate next-hop IP octets
    hop_octets = next_hop.split('.')
    for octet in hop_octets:
        if not 0 <= int(octet) <= 255:
            return False, "Invalid next-hop IP address"

    return True, None

import ipaddress
from flask import Blueprint, render_template, current_app, request, jsonify
from app.auth import login_required
from app.core import mark_config_dirty
from app.modules.interfaces.device import configure_multiple_op

from .utils import (
    ensure_dict,
    get_interface_details,
    get_interface_ip,
    get_next_subnet_id,
    parse_lease_table,
    strip_or_none,
)

dhcp_bp = Blueprint('dhcp', __name__)


def _build_dhcp_set_commands(scope_data, previous_scope=None):  # noqa: ARG001
    """
    Build a list of VyOS commands for configure_set based on scope data.
    Returns a list of command lists that can be sent as a single payload.

    Args:
        scope_data: Current DHCP scope configuration
        previous_scope: Previous scope (reserved for future use)
    """
    commands = []

    shared_network = strip_or_none(scope_data.get("sharedNetwork"))
    subnet = strip_or_none(scope_data.get("subnet"))

    if not shared_network or not subnet:
        raise ValueError("Missing shared network or subnet")

    base_path = ["service", "dhcp-server", "shared-network-name", shared_network]
    subnet_path = base_path + ["subnet", subnet]

    # Authoritative setting
    if scope_data.get("authoritative"):
        commands.append(base_path + ["authoritative"])

    # Subnet options
    default_router = strip_or_none(scope_data.get("defaultRouter"))
    if default_router:
        commands.append(subnet_path + ["option", "default-router", default_router])

    domain_name = strip_or_none(scope_data.get("domainName"))
    if domain_name:
        commands.append(subnet_path + ["option", "domain-name", domain_name])

    # DNS servers
    dns_servers = scope_data.get("dnsServers") or []
    for server in dns_servers:
        server = strip_or_none(server)
        if server:
            commands.append(subnet_path + ["option", "name-server", server])

    # Search domains
    search_domains = scope_data.get("searchDomains") or []
    for domain in search_domains:
        domain = strip_or_none(domain)
        if domain:
            commands.append(subnet_path + ["option", "domain-search", domain])

    # Lease time
    lease = strip_or_none(scope_data.get("lease"))
    if lease:
        commands.append(subnet_path + ["lease", lease])

    # DHCP range
    start_address = strip_or_none(scope_data.get("startAddress"))
    end_address = strip_or_none(scope_data.get("endAddress"))
    if start_address:
        commands.append(subnet_path + ["range", "0", "start", start_address])
    if end_address:
        commands.append(subnet_path + ["range", "0", "stop", end_address])

    # Exclude addresses
    excludes = scope_data.get("excludes") or []
    for exclude in excludes:
        exclude = strip_or_none(exclude)
        if exclude:
            commands.append(subnet_path + ["exclude", exclude])

    # Subnet ID
    subnet_id = strip_or_none(scope_data.get("subnetId"))
    if subnet_id:
        commands.append(subnet_path + ["subnet-id", subnet_id])

    # Static mappings
    static_mappings = scope_data.get("staticMappings") or []
    for mapping in static_mappings:
        name = strip_or_none(mapping.get("name"))
        if not name:
            continue

        mapping_path = subnet_path + ["static-mapping", name]

        mac = strip_or_none(mapping.get("mac"))
        if mac:
            commands.append(mapping_path + ["mac", mac])

        duid = strip_or_none(mapping.get("duid"))
        if duid:
            commands.append(mapping_path + ["duid", duid])

        ip_address = strip_or_none(mapping.get("ipAddress"))
        if ip_address:
            commands.append(mapping_path + ["ip-address", ip_address])

        ipv6_address = strip_or_none(mapping.get("ipv6Address"))
        if ipv6_address:
            commands.append(mapping_path + ["ipv6-address", ipv6_address])

        ipv6_prefix = strip_or_none(mapping.get("ipv6Prefix"))
        if ipv6_prefix:
            commands.append(mapping_path + ["ipv6-prefix", ipv6_prefix])

        hostname = strip_or_none(mapping.get("hostname"))
        if hostname:
            commands.append(mapping_path + ["hostname", hostname])

    return commands


def _build_global_set_commands(global_data):
    """
    Build VyOS commands for global DHCP settings.
    """
    commands = []
    base_path = ["service", "dhcp-server"]

    # Hostfile update
    if global_data.get("hostfileUpdate"):
        commands.append(base_path + ["hostfile-update"])

    # Listen addresses
    listen_addresses = global_data.get("listenAddresses") or []
    for address in listen_addresses:
        address = strip_or_none(address)
        if address:
            commands.append(base_path + ["listen-address", address])

    # High availability
    ha_config = global_data.get("highAvailability") or {}
    if ha_config:
        ha_base = base_path + ["high-availability"]

        mode = strip_or_none(ha_config.get("mode"))
        if mode:
            commands.append(ha_base + ["mode", mode])

        status = strip_or_none(ha_config.get("status"))
        if status:
            commands.append(ha_base + ["status", status])

        source = strip_or_none(ha_config.get("source-address") or ha_config.get("sourceAddress"))
        if source:
            commands.append(ha_base + ["source-address", source])

        remote = strip_or_none(ha_config.get("remote") or ha_config.get("remoteAddress"))
        if remote:
            commands.append(ha_base + ["remote", remote])

        name = strip_or_none(ha_config.get("name"))
        if name:
            commands.append(ha_base + ["name", name])

    return commands


def _build_delete_commands(scope_data, previous_scope):
    """
    Build delete commands for items that were removed.
    Returns a list of paths to delete.
    """
    delete_commands = []

    if not previous_scope:
        return delete_commands

    shared_network = strip_or_none(scope_data.get("sharedNetwork"))
    subnet = strip_or_none(scope_data.get("subnet"))
    prev_shared = strip_or_none(previous_scope.get("sharedNetwork"))
    prev_subnet = strip_or_none(previous_scope.get("subnet"))

    # If shared network or subnet changed, delete the old one entirely
    if prev_shared and prev_subnet:
        if prev_shared != shared_network or prev_subnet != subnet:
            delete_commands.append([
                "service", "dhcp-server", "shared-network-name",
                prev_shared, "subnet", prev_subnet
            ])
            return delete_commands

    base_path = ["service", "dhcp-server", "shared-network-name", shared_network]
    subnet_path = base_path + ["subnet", subnet]

    # Check if authoritative was disabled
    if previous_scope.get("authoritative") and not scope_data.get("authoritative"):
        delete_commands.append(base_path + ["authoritative"])

    # Check for removed static mappings
    prev_mappings = {
        strip_or_none(m.get("name")): m
        for m in (previous_scope.get("staticMappings") or [])
        if strip_or_none(m.get("name"))
    }
    new_mappings = {
        strip_or_none(m.get("name")): m
        for m in (scope_data.get("staticMappings") or [])
        if strip_or_none(m.get("name"))
    }

    for name in prev_mappings:
        if name not in new_mappings:
            delete_commands.append(subnet_path + ["static-mapping", name])

    # Check if excludes were removed (only if we have previous excludes)
    prev_excludes = set(strip_or_none(e) for e in (previous_scope.get("excludes") or []) if strip_or_none(e))
    new_excludes = set(strip_or_none(e) for e in (scope_data.get("excludes") or []) if strip_or_none(e))
    removed_excludes = prev_excludes - new_excludes
    for exclude in removed_excludes:
        delete_commands.append(subnet_path + ["exclude", exclude])

    # Check if DNS servers were removed
    prev_dns = set(strip_or_none(d) for d in (previous_scope.get("dnsServers") or []) if strip_or_none(d))
    new_dns = set(strip_or_none(d) for d in (scope_data.get("dnsServers") or []) if strip_or_none(d))
    removed_dns = prev_dns - new_dns
    for dns_server in removed_dns:
        delete_commands.append(subnet_path + ["option", "name-server", dns_server])

    # Check if search domains were removed
    prev_domains = set(strip_or_none(d) for d in (previous_scope.get("searchDomains") or []) if strip_or_none(d))
    new_domains = set(strip_or_none(d) for d in (scope_data.get("searchDomains") or []) if strip_or_none(d))
    removed_domains = prev_domains - new_domains
    for domain in removed_domains:
        delete_commands.append(subnet_path + ["option", "domain-search", domain])

    return delete_commands


def _build_global_delete_commands(global_data, previous_global):
    """
    Build delete commands for removed global settings.
    """
    delete_commands = []

    if not previous_global:
        return delete_commands

    base_path = ["service", "dhcp-server"]

    # Check if hostfile-update was disabled
    if previous_global.get("hostfileUpdate") and not global_data.get("hostfileUpdate"):
        delete_commands.append(base_path + ["hostfile-update"])

    # Check if HA was removed
    prev_ha = previous_global.get("highAvailability")
    new_ha = global_data.get("highAvailability")
    if prev_ha and not new_ha:
        delete_commands.append(base_path + ["high-availability"])

    # Check for removed listen addresses
    prev_listen = set(strip_or_none(a) for a in (previous_global.get("listenAddresses") or []) if strip_or_none(a))
    new_listen = set(strip_or_none(a) for a in (global_data.get("listenAddresses") or []) if strip_or_none(a))
    removed_listen = prev_listen - new_listen
    for address in removed_listen:
        delete_commands.append(base_path + ["listen-address", address])

    return delete_commands


@dhcp_bp.route('/dhcp')
@login_required
def dhcp():
    """Main DHCP page - shows interface list"""
    device = current_app.device
    config_data = device.retrieve_show_config(path=["interfaces"])
    # retrieve_show_config returns dict directly, not JSON string
    config = config_data.result if config_data and config_data.result else {}

    interfaces = {}
    ethernet = config.get("ethernet", {})
    for iface, info in ethernet.items():
        interfaces[iface] = {
            "description": info.get("description", ""),
            "address": info.get("address", []),
        }
        # Include VLANs
        for vlan_id, vlan_info in info.get("vif", {}).items():
            vlan_name = f"{iface}.{vlan_id}"
            interfaces[vlan_name] = {
                "description": vlan_info.get("description", ""),
                "address": vlan_info.get("address", []),
                "parent": iface,
            }

    next_subnet_id = get_next_subnet_id(device)
    return render_template('dhcp/dhcp.html', interfaces=interfaces, next_subnet_id=next_subnet_id)


@dhcp_bp.route('/services/dhcp/<iface>', methods=['GET'])
@login_required
def get_dhcp(iface):
    """Get DHCP configuration for a specific interface"""
    device = current_app.device

    # Get interface configuration
    iface_data = device.retrieve_show_config(path=["interfaces"])
    iface_config = iface_data.result if iface_data and iface_data.result else {}

    # Get DHCP server configuration
    dhcp_data = device.retrieve_show_config(path=["service", "dhcp-server"])
    dhcp_config = dhcp_data.result if dhcp_data and dhcp_data.result else {}

    # Get interface details
    interface_details = get_interface_details(iface_config, iface)
    description = interface_details.get("description", "")
    addresses = interface_details.get("addresses", [])
    interface_ip = get_interface_ip(addresses)

    # Log for debugging
    current_app.logger.debug(f"Interface: {iface}, Description: {description}, Addresses: {addresses}")

    # Get subnets for this interface
    def to_subnet(addr: str):
        if "/" not in addr:
            return None
        try:
            network = strip_or_none(addr)
            if not network:
                return None
            return str(ipaddress.ip_network(network, strict=False))
        except ValueError:
            return None

    iface_subnets = [to_subnet(addr) for addr in addresses if addr]
    iface_subnets = [subnet for subnet in iface_subnets if subnet]

    # Look for matching DHCP configuration
    shared_networks = ensure_dict(dhcp_config.get("shared-network-name"))
    matched = None

    current_app.logger.debug(f"Available shared networks: {list(shared_networks.keys())}")
    current_app.logger.debug(f"Interface subnets: {iface_subnets}")

    for shared_name, shared_info in shared_networks.items():
        shared_map = ensure_dict(shared_info)
        shared_enabled = "disable" not in shared_map
        shared_authoritative = "authoritative" in shared_map

        subnet_container = ensure_dict(shared_map.get("subnet"))
        for subnet_value, subnet_info in subnet_container.items():
            current_app.logger.debug(f"Checking shared network '{shared_name}' with subnet '{subnet_value}' against interface subnets {iface_subnets}")
            # Check if this subnet matches the interface
            if iface_subnets and subnet_value not in iface_subnets:
                current_app.logger.debug(f"Subnet {subnet_value} not in interface subnets, skipping")
                continue

            subnet_map = ensure_dict(subnet_info)
            subnet_enabled = "disable" not in subnet_map
            subnet_option_map = ensure_dict(subnet_map.get("option"))

            # Parse options
            default_router = strip_or_none(subnet_option_map.get("default-router")) or interface_ip or ""
            domain_name = strip_or_none(subnet_option_map.get("domain-name")) or ""

            # Parse name servers
            name_servers = []
            ns_value = subnet_option_map.get("name-server")
            if isinstance(ns_value, list):
                name_servers = [strip_or_none(ns) for ns in ns_value if strip_or_none(ns)]
            elif ns_value:
                name_servers = [strip_or_none(ns_value)]

            # Parse domain search
            search_domains = []
            ds_value = subnet_option_map.get("domain-search")
            if isinstance(ds_value, list):
                search_domains = [strip_or_none(ds) for ds in ds_value if strip_or_none(ds)]
            elif ds_value:
                search_domains = [strip_or_none(ds_value)]

            # Parse lease
            lease_value = strip_or_none(subnet_map.get("lease")) or "86400"

            # Parse subnet ID
            subnet_id_value = strip_or_none(subnet_map.get("subnet-id")) or ""

            # Parse excludes
            excludes = []
            exclude_value = subnet_map.get("exclude")
            if isinstance(exclude_value, list):
                excludes = [strip_or_none(e) for e in exclude_value if strip_or_none(e)]
            elif exclude_value:
                excludes = [strip_or_none(exclude_value)]

            # Parse range
            start_address = ""
            end_address = ""
            range_container = ensure_dict(subnet_map.get("range"))
            if range_container:
                range_0 = ensure_dict(range_container.get("0"))
                start_address = strip_or_none(range_0.get("start")) or ""
                end_address = strip_or_none(range_0.get("stop")) or ""

            # Parse static mappings
            static_mappings = []
            static_container = ensure_dict(subnet_map.get("static-mapping"))
            for mapping_name, mapping_details in static_container.items():
                mapping_map = ensure_dict(mapping_details)
                entry = {"name": strip_or_none(mapping_name) or ""}

                if "mac" in mapping_map:
                    entry["mac"] = strip_or_none(mapping_map.get("mac")) or ""
                if "duid" in mapping_map:
                    entry["duid"] = strip_or_none(mapping_map.get("duid")) or ""
                if "ip-address" in mapping_map:
                    entry["ipAddress"] = strip_or_none(mapping_map.get("ip-address")) or ""
                if "ipv6-address" in mapping_map:
                    entry["ipv6Address"] = strip_or_none(mapping_map.get("ipv6-address")) or ""
                if "ipv6-prefix" in mapping_map:
                    entry["ipv6Prefix"] = strip_or_none(mapping_map.get("ipv6-prefix")) or ""
                if "hostname" in mapping_map:
                    entry["hostname"] = strip_or_none(mapping_map.get("hostname")) or ""

                static_mappings.append(entry)

            matched = {
                "sharedNetwork": shared_name,
                "subnet": subnet_value,
                "subnetId": subnet_id_value,
                "defaultRouter": default_router,
                "domainName": domain_name or "vyos.net",
                "dnsServers": name_servers,
                "searchDomains": search_domains,
                "startAddress": start_address,
                "endAddress": end_address,
                "lease": lease_value,
                "excludes": excludes,
                "authoritative": shared_authoritative,
                "staticMappings": static_mappings,
                "enabled": shared_enabled and subnet_enabled,
                "isConfigured": True,
            }
            break

        if matched:
            break

    # If no configuration found by subnet match, try to find any DHCP config
    # that uses the interface name or description as the shared network name
    if not matched:
        current_app.logger.debug(f"No subnet match found. Trying name match...")
        current_app.logger.debug(f"Checking if any shared network name matches iface='{iface}' or description='{description}'")
        # Try to find a shared network that matches the interface name or description
        for shared_name, shared_info in shared_networks.items():
            # Check if shared network name matches interface name or description
            current_app.logger.debug(f"Comparing shared_name='{shared_name}' against iface='{iface}' and description='{description}'")
            if shared_name.lower() in [iface.lower(), description.lower()]:
                shared_map = ensure_dict(shared_info)
                shared_enabled = "disable" not in shared_map
                shared_authoritative = "authoritative" in shared_map

                subnet_container = ensure_dict(shared_map.get("subnet"))
                # Get the first subnet from this shared network
                for subnet_value, subnet_info in subnet_container.items():
                    subnet_map = ensure_dict(subnet_info)
                    subnet_enabled = "disable" not in subnet_map
                    subnet_option_map = ensure_dict(subnet_map.get("option"))

                    # Parse all the configuration (same as above)
                    default_router = strip_or_none(subnet_option_map.get("default-router")) or interface_ip or ""
                    domain_name = strip_or_none(subnet_option_map.get("domain-name")) or ""

                    name_servers = []
                    ns_value = subnet_option_map.get("name-server")
                    if isinstance(ns_value, list):
                        name_servers = [strip_or_none(ns) for ns in ns_value if strip_or_none(ns)]
                    elif ns_value:
                        name_servers = [strip_or_none(ns_value)]

                    search_domains = []
                    ds_value = subnet_option_map.get("domain-search")
                    if isinstance(ds_value, list):
                        search_domains = [strip_or_none(ds) for ds in ds_value if strip_or_none(ds)]
                    elif ds_value:
                        search_domains = [strip_or_none(ds_value)]

                    lease_value = strip_or_none(subnet_map.get("lease")) or "86400"
                    subnet_id_value = strip_or_none(subnet_map.get("subnet-id")) or ""

                    excludes = []
                    exclude_value = subnet_map.get("exclude")
                    if isinstance(exclude_value, list):
                        excludes = [strip_or_none(e) for e in exclude_value if strip_or_none(e)]
                    elif exclude_value:
                        excludes = [strip_or_none(exclude_value)]

                    start_address = ""
                    end_address = ""
                    range_container = ensure_dict(subnet_map.get("range"))
                    if range_container:
                        range_0 = ensure_dict(range_container.get("0"))
                        start_address = strip_or_none(range_0.get("start")) or ""
                        end_address = strip_or_none(range_0.get("stop")) or ""

                    static_mappings = []
                    static_container = ensure_dict(subnet_map.get("static-mapping"))
                    for mapping_name, mapping_details in static_container.items():
                        mapping_map = ensure_dict(mapping_details)
                        entry = {"name": strip_or_none(mapping_name) or ""}

                        if "mac" in mapping_map:
                            entry["mac"] = strip_or_none(mapping_map.get("mac")) or ""
                        if "duid" in mapping_map:
                            entry["duid"] = strip_or_none(mapping_map.get("duid")) or ""
                        if "ip-address" in mapping_map:
                            entry["ipAddress"] = strip_or_none(mapping_map.get("ip-address")) or ""
                        if "ipv6-address" in mapping_map:
                            entry["ipv6Address"] = strip_or_none(mapping_map.get("ipv6-address")) or ""
                        if "ipv6-prefix" in mapping_map:
                            entry["ipv6Prefix"] = strip_or_none(mapping_map.get("ipv6-prefix")) or ""
                        if "hostname" in mapping_map:
                            entry["hostname"] = strip_or_none(mapping_map.get("hostname")) or ""

                        static_mappings.append(entry)

                    matched = {
                        "sharedNetwork": shared_name,
                        "subnet": subnet_value,
                        "subnetId": subnet_id_value,
                        "defaultRouter": default_router,
                        "domainName": domain_name or "vyos.net",
                        "dnsServers": name_servers,
                        "searchDomains": search_domains,
                        "startAddress": start_address,
                        "endAddress": end_address,
                        "lease": lease_value,
                        "excludes": excludes,
                        "authoritative": shared_authoritative,
                        "staticMappings": static_mappings,
                        "enabled": shared_enabled and subnet_enabled,
                        "isConfigured": True,
                    }
                    break

                if matched:
                    break

    # If still no configuration found, return defaults for creating new
    if not matched:
        default_shared_name = description or iface
        default_subnet = iface_subnets[0] if iface_subnets else ""
        matched = {
            "sharedNetwork": default_shared_name,
            "subnet": default_subnet,
            "subnetId": "",
            "defaultRouter": strip_or_none(interface_ip) or "",
            "domainName": "vyos.net",
            "dnsServers": [],
            "searchDomains": [],
            "startAddress": "",
            "endAddress": "",
            "lease": "86400",
            "excludes": [],
            "authoritative": False,
            "staticMappings": [],
            "enabled": False,
            "isConfigured": False,
        }

    # Parse global settings
    global_settings = {
        "hostfileUpdate": "hostfile-update" in dhcp_config,
        "listenAddresses": [],
        "highAvailability": {},
    }

    # Parse listen addresses
    listen_value = dhcp_config.get("listen-address")
    if isinstance(listen_value, list):
        global_settings["listenAddresses"] = [strip_or_none(addr) for addr in listen_value if strip_or_none(addr)]
    elif listen_value:
        global_settings["listenAddresses"] = [strip_or_none(listen_value)]

    # Parse HA settings
    ha_config = ensure_dict(dhcp_config.get("high-availability"))
    if ha_config:
        ha_settings = {}
        if "mode" in ha_config:
            ha_settings["mode"] = strip_or_none(ha_config.get("mode"))
        if "status" in ha_config:
            ha_settings["status"] = strip_or_none(ha_config.get("status"))
        if "source-address" in ha_config:
            ha_settings["source-address"] = strip_or_none(ha_config.get("source-address"))
        if "remote" in ha_config:
            ha_settings["remote"] = strip_or_none(ha_config.get("remote"))
        if "name" in ha_config:
            ha_settings["name"] = strip_or_none(ha_config.get("name"))
        global_settings["highAvailability"] = ha_settings

    matched["interfaceDescription"] = description
    matched["interfaceIp"] = interface_ip
    matched["nextAvailableSubnetId"] = str(get_next_subnet_id(device))
    matched["globalSettings"] = global_settings

    return matched


@dhcp_bp.route('/services/dhcp/<iface>/leases', methods=['GET'])
@login_required
def list_leases(iface):
    """Get active DHCP leases for an interface"""
    try:
        scope = get_dhcp(iface)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500

    # Get the shared network name (this is the pool name)
    shared_network = strip_or_none(scope.get("sharedNetwork"))

    if not shared_network:
        # No shared network configured, return empty leases
        return jsonify({"status": "ok", "data": []})

    leases = []
    try:
        # Query leases for the specific pool (shared-network-name)
        import json
        response = current_app.device.show(path=["dhcp", "server", "leases", "pool", shared_network])
        raw_result = getattr(response, "result", "") or ""

        if not raw_result or not raw_result.strip():
            # No leases for this pool
            return jsonify({"status": "ok", "data": []})

        # Parse the table output into JSON
        lines = [line.rstrip() for line in raw_result.strip().splitlines() if line.strip()]

        if len(lines) < 3:
            # Not enough lines for a valid table (header, separator, data)
            return jsonify({"status": "ok", "data": []})

        # Extract headers from first line
        headers = [h.strip() for h in lines[0].split("  ") if h.strip()]

        # Data rows start after the dashed separator (line 2)
        rows = lines[2:]

        # Parse each row
        for row in rows:
            # Split on multiple spaces, filter empty
            values = [v.strip() for v in row.split("  ") if v.strip()]
            if len(values) >= len(headers):
                record = dict(zip(headers, values))

                # Normalize keys for frontend compatibility
                # Convert "IP Address" -> "ip", "MAC address" -> "mac", etc.
                normalized = {
                    "ip": record.get("IP Address", record.get("IP address", "")),
                    "mac": record.get("MAC address", record.get("MAC Address", "")),
                    "state": record.get("State", ""),
                    "lease_start": record.get("Lease start", ""),
                    "lease_expiration": record.get("Lease expiration", ""),
                    "remaining": record.get("Remaining", ""),
                    "pool": record.get("Pool", ""),
                    "hostname": record.get("Hostname", ""),
                    "origin": record.get("Origin", ""),
                }

                leases.append(normalized)

        current_app.logger.debug(f"Parsed {len(leases)} leases for pool '{shared_network}'")

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch leases for pool '{shared_network}': {exc}")
        import traceback
        traceback.print_exc()
        leases = []

    return jsonify({"status": "ok", "data": leases})


def _validate_payload(data):
    """Validate DHCP configuration payload"""
    if not data:
        raise ValueError("Missing payload")

    shared_network = strip_or_none(data.get("sharedNetwork"))
    subnet = strip_or_none(data.get("subnet"))
    if not shared_network or not subnet:
        raise ValueError("Missing required fields: sharedNetwork, subnet")

    default_router = strip_or_none(data.get("defaultRouter"))
    domain_name = strip_or_none(data.get("domainName"))
    lease = strip_or_none(data.get("lease"))
    start_address = strip_or_none(data.get("startAddress"))
    end_address = strip_or_none(data.get("endAddress"))

    if not default_router:
        raise ValueError("Missing required field: defaultRouter")
    if not domain_name:
        raise ValueError("Missing required field: domainName")
    if not lease:
        raise ValueError("Missing required field: lease")
    if not start_address or not end_address:
        raise ValueError("Missing required DHCP range definition (startAddress / endAddress)")

    dns_servers = data.get("dnsServers") or []
    if not any(strip_or_none(entry) for entry in dns_servers):
        raise ValueError("Provide at least one DNS server")


@dhcp_bp.route('/services/dhcp/<iface>/create', methods=['POST'])
@login_required
def create_dhcp(iface):
    """Create new DHCP configuration for an interface"""
    payload = request.get_json() or {}
    data = payload.get("data", payload)
    global_settings = payload.get("global") or {}

    try:
        _validate_payload(data)
        existing = get_dhcp(iface)

        if existing.get("isConfigured"):
            return jsonify({
                "status": "error",
                "message": "DHCP configuration already exists for this interface."
            }), 400

        # Set subnet ID if not provided
        subnet_id = (
            data.get("subnetId")
            or data.get("subnet_id")
            or existing.get("nextAvailableSubnetId")
            or str(get_next_subnet_id(current_app.device))
        )
        data["subnetId"] = subnet_id

        # Build set commands
        set_commands = _build_dhcp_set_commands(data)
        global_commands = _build_global_set_commands(global_settings)
        all_commands = set_commands + global_commands

        # Handle disable state
        if not data.get("enabled", True):
            shared_network = strip_or_none(data.get("sharedNetwork"))
            disable_cmd = ["service", "dhcp-server", "shared-network-name", shared_network, "disable"]
            all_commands.append(disable_cmd)

        current_app.logger.debug("DHCP create commands: %s", all_commands)

        # Build operations for configure_multiple_op
        operations = [{"op": "set", "path": path} for path in all_commands]

        # Execute all operations in a single batch
        if operations:
            success, error_message = configure_multiple_op(
                operations,
                error_context="create DHCP configuration"
            )

            if not success:
                raise RuntimeError(error_message or "Failed to create DHCP configuration")

        # Mark configuration as dirty (unsaved changes)
        mark_config_dirty()

        refreshed = get_dhcp(iface)
        return jsonify({"status": "ok", "created": True, "data": refreshed, "config_dirty": True})

    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@dhcp_bp.route('/services/dhcp/<iface>/update', methods=['POST'])
@login_required
def update_dhcp(iface):
    """Update existing DHCP configuration for an interface"""
    payload = request.get_json() or {}
    data = payload.get("data", payload)
    global_settings = payload.get("global") or {}

    try:
        _validate_payload(data)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    try:
        existing = get_dhcp(iface)

        if not existing.get("isConfigured"):
            return jsonify({
                "status": "error",
                "message": "No DHCP configuration exists for this interface. Use create instead."
            }), 400

        # Preserve subnet ID if not provided
        subnet_id = (
            data.get("subnetId")
            or data.get("subnet_id")
            or existing.get("subnetId")
            or existing.get("nextAvailableSubnetId")
            or str(get_next_subnet_id(current_app.device))
        )
        data["subnetId"] = subnet_id

        # Build commands
        delete_commands = _build_delete_commands(data, existing)
        set_commands = _build_dhcp_set_commands(data, existing)

        global_delete_commands = _build_global_delete_commands(global_settings, existing.get("globalSettings"))
        global_set_commands = _build_global_set_commands(global_settings)

        all_delete = delete_commands + global_delete_commands
        all_set = set_commands + global_set_commands

        current_app.logger.debug("DHCP update delete: %s", all_delete)
        current_app.logger.debug("DHCP update set: %s", all_set)

        # Handle enable/disable state
        shared_network = strip_or_none(data.get("sharedNetwork"))
        base_path = ["service", "dhcp-server", "shared-network-name", shared_network]

        if data.get("enabled", True):
            # Remove disable flag if exists
            all_delete.append(base_path + ["disable"])
        else:
            # Add disable flag
            all_set.append(base_path + ["disable"])

        # Build operations for configure_multiple_op (delete first, then set)
        operations = []
        operations.extend([{"op": "delete", "path": path} for path in all_delete])
        operations.extend([{"op": "set", "path": path} for path in all_set])

        # Execute all operations in a single batch
        if operations:
            success, error_message = configure_multiple_op(
                operations,
                error_context="update DHCP configuration"
            )

            if not success:
                raise RuntimeError(error_message or "Failed to update DHCP configuration")

        # Mark configuration as dirty (unsaved changes)
        mark_config_dirty()

        refreshed = get_dhcp(iface)
        return jsonify({"status": "ok", "created": False, "data": refreshed, "config_dirty": True})

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500


@dhcp_bp.route('/services/dhcp/<iface>/delete', methods=['POST'])
@login_required
def delete_dhcp(iface):
    """Delete DHCP configuration for an interface"""
    try:
        existing = get_dhcp(iface)

        if not existing.get("isConfigured"):
            return jsonify({
                "status": "error",
                "message": "No DHCP configuration exists for this interface."
            }), 400

        shared_network = strip_or_none(existing.get("sharedNetwork"))
        subnet = strip_or_none(existing.get("subnet"))

        if not shared_network or not subnet:
            return jsonify({
                "status": "error",
                "message": "Invalid configuration state."
            }), 400

        device = current_app.device

        # Delete the subnet
        delete_path = [
            "service", "dhcp-server", "shared-network-name",
            shared_network, "subnet", subnet
        ]
        device.configure_delete(path=delete_path)

        # Mark configuration as dirty (unsaved changes)
        mark_config_dirty()

        return jsonify({"status": "ok", "deleted": True, "config_dirty": True})

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(exc)}), 500

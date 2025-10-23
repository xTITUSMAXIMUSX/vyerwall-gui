import re
from typing import Iterable, List, Optional, Tuple, Dict, Set

from flask import Blueprint, current_app, render_template, request

from auth_utils import login_required
from .device import configure_set
from .dhcp import (
    build_dhcp_paths,
    build_dns_paths,
    dns_cache_commands,
    get_next_subnet_id,
    has_active_dhcp_scope,
    load_dhcp_config,
)
from .nat import (
    build_nat_rule_commands,
    build_nat_rule_update_commands,
    find_nat_rule_for_iface,
    load_nat_source_rules,
    map_nat_assignments,
    next_nat_rule_number,
    reorder_managed_nat_rules,
)
from .util import (
    extract_configured_interfaces,
    flatten_interface_config,
    is_valid_cidr,
    load_cidr_network,
    normalise_iface_name,
)
from .zone import (
    build_zone_definition_commands,
    build_zone_membership_commands,
    build_zone_membership_delete,
    find_zone_for_interface,
    list_zones,
    load_zone_config,
    map_zone_members,
    sanitise_zone_name,
)

interfaces_bp = Blueprint("interfaces", __name__)


def _dedupe(commands: Iterable[List[str]]) -> List[List[str]]:
    deduped: List[List[str]] = []
    seen = set()
    for cmd in commands:
        tuple_cmd = tuple(cmd)
        if tuple_cmd in seen:
            continue
        seen.add(tuple_cmd)
        deduped.append(cmd)
    return deduped


def _parse_interface_detail(raw_output: str) -> Tuple[dict, set[str]]:
    parsed_interfaces = {}
    current_iface = None
    rx_headers = tx_headers = []
    prev_line = ""
    all_base_ifaces = set()

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue

        if re.match(r"^[a-zA-Z0-9\.\-@]+: <", line):
            current_iface = line.split(":")[0]
            parsed_interfaces[current_iface] = {
                "state": None,
                "mtu": None,
                "mac": None,
                "inet": [],
                "inet6": [],
                "description": None,
                "rx": {},
                "tx": {},
            }

            if "mtu" in line:
                parts = line.split()
                if "mtu" in parts:
                    parsed_interfaces[current_iface]["mtu"] = parts[parts.index("mtu") + 1]
                if "state" in parts:
                    parsed_interfaces[current_iface]["state"] = parts[parts.index("state") + 1]
        elif not current_iface:
            continue
        elif line.startswith("link/ether"):
            parsed_interfaces[current_iface]["mac"] = line.split()[1]
        elif line.startswith("inet "):
            parsed_interfaces[current_iface]["inet"].append(line.split()[1])
        elif line.startswith("inet6"):
            parsed_interfaces[current_iface]["inet6"].append(line.split()[1])
        elif line.startswith("Description:"):
            parsed_interfaces[current_iface]["description"] = line.split(":", 1)[1].strip()
        elif line.startswith("RX:"):
            rx_headers = line.replace("RX:", "").split()
        elif line.startswith("TX:"):
            tx_headers = line.replace("TX:", "").split()
        elif re.match(r"^\d", line):
            values = line.split()
            if prev_line.startswith("RX:"):
                parsed_interfaces[current_iface]["rx"] = dict(zip(rx_headers, values))
            elif prev_line.startswith("TX:"):
                parsed_interfaces[current_iface]["tx"] = dict(zip(tx_headers, values))

        if current_iface:
            normalised = normalise_iface_name(current_iface)
            if normalised and "." not in normalised and normalised.startswith("eth"):
                all_base_ifaces.add(normalised)

        prev_line = line

    return parsed_interfaces, all_base_ifaces


def _load_existing_address(iface: str) -> Optional[str]:
    iface_lookup = normalise_iface_name(iface)
    if not iface_lookup:
        return None
    try:
        existing_config = current_app.device.retrieve_show_config(path=["interfaces"])
        config_result = getattr(existing_config, "result", {}) or {}
        previous_details = flatten_interface_config(config_result).get(iface_lookup, {})
        return previous_details.get("address")
    except Exception:
        return None


@interfaces_bp.route("/interfaces")
@login_required
def interfaces():
    detail_data = current_app.device.show(path=["interfaces", "ethernet", "detail"])
    raw_output = getattr(detail_data, "result", "") or ""

    config_data = current_app.device.retrieve_show_config(path=["interfaces"])
    config_result = getattr(config_data, "result", {}) or {}
    configured_names = extract_configured_interfaces(config_result)
    config_map = flatten_interface_config(config_result)

    parsed_interfaces, all_base_ifaces = _parse_interface_detail(raw_output)
    zone_config = load_zone_config()
    zone_names = {sanitise_zone_name(zone) for zone in list_zones(zone_config)}
    zone_names.discard("")
    available_zones = sorted(zone_names)

    active_interfaces = {}
    for name, info in parsed_interfaces.items():
        normalised = normalise_iface_name(name)
        if not normalised:
            continue

        if normalised in config_map:
            config_details = config_map[normalised]
            config_address = config_details.get("address")
            address_mode = None
            if isinstance(config_address, str) and config_address.lower() == "dhcp":
                address_mode = "dhcp"
            elif config_address:
                address_mode = "static"

            info["config_address"] = config_address
            info["address_mode"] = address_mode

            if not info.get("description") and config_details.get("description"):
                info["description"] = config_details["description"]

        if normalised in configured_names:
            active_interfaces[name] = info
            zone_assignment = find_zone_for_interface(normalised, zone_config)
            info["zone"] = sanitise_zone_name(zone_assignment) if zone_assignment else None

    available_interfaces = sorted(
        iface for iface in all_base_ifaces if iface not in configured_names
    )

    nat_assignments = map_nat_assignments()
    for name, info in active_interfaces.items():
        normalised_name = normalise_iface_name(name)
        assignment = nat_assignments.get(normalised_name or "", {})
        info["source_nat_interface"] = assignment.get("outbound") or ""
        info["nat_rule_number"] = assignment.get("rule")

    return render_template(
        "interfaces/index.html",
        interfaces=active_interfaces,
        available_interfaces=available_interfaces,
        source_nat_interfaces=sorted(all_base_ifaces),
        zones=available_zones,
    )


@interfaces_bp.route("/interfaces/disable/<iface>", methods=["POST"])
@login_required
def interfaces_disable(iface):
    if "@" in iface:
        vlan_id = iface.split("@")[0].split(".")[1]
        parent_interface = iface.split("@")[1]
        current_app.device.configure_set(
            path=["interfaces", "ethernet", parent_interface, "vif", vlan_id, "disable"]
        )
    else:
        current_app.device.configure_set(
            path=["interfaces", "ethernet", iface, "disable"]
        )

    return {"status": "ok", "action": "disabled", "iface": iface}


@interfaces_bp.route("/interfaces/enable/<iface>", methods=["POST"])
@login_required
def interfaces_enable(iface):
    if "@" in iface:
        vlan_id = iface.split("@")[0].split(".")[1]
        parent_interface = iface.split("@")[1]
        current_app.device.configure_delete(
            path=["interfaces", "ethernet", parent_interface, "vif", vlan_id, "disable"]
        )
    else:
        current_app.device.configure_delete(
            path=["interfaces", "ethernet", iface, "disable"]
        )

    return {"status": "ok", "action": "enabled", "iface": iface}


@interfaces_bp.route("/interfaces/edit/<iface>", methods=["POST"])
@login_required
def interfaces_edit(iface):
    data = request.get_json()
    description = data.get("description")
    address = data.get("address")
    mode = (data.get("mode") or "").strip().lower()
    zone_field = data.get("zone")
    zone_name = sanitise_zone_name(zone_field) if zone_field is not None else None

    if mode not in {"dhcp", "static"}:
        return {"status": "error", "message": "Mode must be either DHCP or Static."}, 400
    if zone_field is not None and zone_field != "" and not zone_name:
        return {"status": "error", "message": "Zone assignment is required."}, 400

    if "@" in iface:
        vlan_id = iface.split("@")[0].split(".")[1]
        parent_interface = iface.split("@")[1]
        base_path = ["interfaces", "ethernet", parent_interface, "vif", vlan_id]
    else:
        base_path = ["interfaces", "ethernet", iface]

    iface_lookup = normalise_iface_name(iface)
    previous_address = _load_existing_address(iface)

    set_commands: List[List[str]] = []
    if description:
        set_commands.append(base_path + ["description", description])

    if mode == "dhcp":
        address = "dhcp"
    elif mode == "static":
        if not address or not is_valid_cidr(address):
            return {"status": "error", "message": "Static mode requires a valid CIDR address."}, 400

    source_nat_iface = (data.get("source_nat_interface") or "").strip()
    if source_nat_iface and not source_nat_iface.startswith("eth"):
        return {"status": "error", "message": "Source NAT interface must be an ethernet interface (e.g. eth0)."}, 400

    if address:
        try:
            current_app.device.configure_delete(path=base_path + ["address"])
        except Exception:
            pass

        set_commands.append(base_path + ["address", address])

    zone_config_snapshot = load_zone_config()
    membership_map = map_zone_members(zone_config_snapshot)
    sanitized_membership: Dict[str, Set[str]] = {}
    for zone_key, members in membership_map.items():
        sanitized_key = sanitise_zone_name(zone_key)
        sanitized_membership[sanitized_key] = {
            (normalise_iface_name(member) or member).lower() for member in members
        }

    initial_zone = find_zone_for_interface(iface_lookup or iface, zone_config_snapshot)
    initial_zone_key = sanitise_zone_name(initial_zone) if initial_zone else None
    iface_membership_key = (iface_lookup or iface).lower()
    zone_add_commands: List[List[str]] = []
    zone_remove_commands: List[List[str]] = []

    def zone_has_other_members(zone_key: Optional[str]) -> bool:
        if not zone_key:
            return True
        members = sanitized_membership.get(zone_key, set())
        remaining = {member for member in members if member != iface_membership_key}
        return bool(remaining)

    if zone_field is not None:
        if zone_name:
            zone_add_commands.extend(build_zone_definition_commands(zone_name, zone_config_snapshot))
            if not initial_zone or (initial_zone_key != zone_name):
                if initial_zone_key:
                    if not zone_has_other_members(initial_zone_key):
                        return {
                            "status": "error",
                            "message": f"Zone {initial_zone_key} must retain at least one interface.",
                        }, 400
                    zone_remove_commands.extend(
                        build_zone_membership_delete(initial_zone, iface_lookup or iface)
                    )
                zone_add_commands.extend(build_zone_membership_commands(zone_name, iface_lookup or iface))
        elif initial_zone_key:
            if not zone_has_other_members(initial_zone_key):
                return {
                    "status": "error",
                    "message": f"Zone {initial_zone_key} must retain at least one interface.",
                }, 400
            zone_remove_commands.extend(
                build_zone_membership_delete(initial_zone, iface_lookup or iface)
            )
    elif zone_name:
        zone_add_commands.extend(build_zone_definition_commands(zone_name, zone_config_snapshot))
        if not initial_zone or (initial_zone_key != zone_name):
            if initial_zone_key:
                if not zone_has_other_members(initial_zone_key):
                    return {
                        "status": "error",
                        "message": f"Zone {initial_zone_key} must retain at least one interface.",
                    }, 400
                zone_remove_commands.extend(
                    build_zone_membership_delete(initial_zone, iface_lookup or iface)
                )
            zone_add_commands.extend(build_zone_membership_commands(zone_name, iface_lookup or iface))

    if zone_remove_commands:
        zone_remove_commands = _dedupe(zone_remove_commands)
        response = current_app.device.configure_delete(path=zone_remove_commands)
        if getattr(response, "error", None):
            return {"status": "error", "message": response.error}, 500
        status_code = getattr(response, "status", 200)
        if status_code != 200:
            return {
                "status": "error",
                "message": f"Device returned status {status_code} while updating zone membership",
            }, 500

    set_commands.extend(zone_add_commands)

    if set_commands:
        set_commands = _dedupe(set_commands)
        success, error_message = configure_set(set_commands, error_context=f"interface {iface_lookup}")
        if not success:
            return {"status": "error", "message": error_message}, 500

    nat_rules = load_nat_source_rules()
    nat_rule_hint = data.get("nat_rule_number")
    existing_rule_number = None
    if nat_rule_hint is not None:
        try:
            nat_rule_candidate = int(str(nat_rule_hint).strip())
            if nat_rule_candidate in nat_rules:
                existing_rule_number = nat_rule_candidate
        except (TypeError, ValueError):
            existing_rule_number = None

    candidate_network = load_cidr_network(address) if mode == "static" else None
    previous_network = load_cidr_network(previous_address)
    if existing_rule_number is None:
        existing_rule_number, _ = find_nat_rule_for_iface(
            nat_rules,
            iface_lookup or iface,
            candidate_network,
        )
    if existing_rule_number is None and previous_network:
        existing_rule_number, _ = find_nat_rule_for_iface(
            nat_rules,
            iface_lookup or iface,
            previous_network,
        )

    applied_nat_rule_number = existing_rule_number

    if source_nat_iface:
        if mode != "static":
            return {"status": "error", "message": "Source NAT requires a static address."}, 400

        source_network = candidate_network or load_cidr_network(address)
        if not source_network:
            return {"status": "error", "message": "Unable to derive source network for NAT."}, 400

        if existing_rule_number is not None:
            nat_commands = build_nat_rule_update_commands(
                existing_rule_number,
                source_nat_iface,
                source_network,
                iface_lookup or iface,
            )
            applied_nat_rule_number = existing_rule_number
        else:
            rule_number = next_nat_rule_number(nat_rules)
            nat_commands = build_nat_rule_commands(
                rule_number,
                source_nat_iface,
                source_network,
                iface_lookup or iface,
            )
            applied_nat_rule_number = rule_number

        success, error_message = configure_set(nat_commands, error_context=f"NAT rule for {iface_lookup or iface}")
        if not success:
            return {"status": "error", "message": error_message}, 500
    else:
        if existing_rule_number is not None:
            response = current_app.device.configure_delete(
                path=[["nat", "source", "rule", str(existing_rule_number)]]
            )
            if getattr(response, "error", None):
                return {"status": "error", "message": response.error}, 500
            status = getattr(response, "status", 200)
            if status != 200:
                return {
                    "status": "error",
                    "message": f"Device returned status {status} while deleting NAT rule",
                }, 500
            reorder_success, reorder_error = reorder_managed_nat_rules()
            if not reorder_success:
                return {"status": "error", "message": reorder_error}, 500
            applied_nat_rule_number = None

    updated_zone = zone_name or (sanitise_zone_name(initial_zone) if initial_zone else None)
    return {
        "status": "ok",
        "iface": iface,
        "nat_rule_number": applied_nat_rule_number,
        "zone": updated_zone,
    }


def _build_base_interface_commands(base_path: List[str], description: Optional[str], address: Optional[str]) -> List[List[str]]:
    commands: List[List[str]] = [base_path]
    if description:
        commands.append(base_path + ["description", description])
    if address:
        commands.append(base_path + ["address", address])
    return commands


def _augment_with_services(commands: List[List[str]], address: Optional[str], description: Optional[str], shared_default: str):
    if not address:
        return

    dhcp_config = load_dhcp_config()
    shared_name = description or shared_default
    subnet_id = get_next_subnet_id(dhcp_config)
    dhcp_paths = build_dhcp_paths(shared_name, address, subnet_id=subnet_id)
    commands.extend(dhcp_paths)
    if has_active_dhcp_scope(dhcp_config):
        commands.append(["service", "dhcp-server", "shared-network-name", shared_name, "disable"])

    dns_commands, _, _ = build_dns_paths(address)
    commands.extend(dns_commands)
    commands.extend(dns_cache_commands())


def _append_nat_commands(commands: List[List[str]], address: Optional[str], source_nat_iface: Optional[str], identity: str):
    if not source_nat_iface:
        return

    source_network = load_cidr_network(address)
    if not source_network:
        raise ValueError("Unable to derive source network for NAT.")

    nat_rules = load_nat_source_rules()
    rule_number = next_nat_rule_number(nat_rules)
    commands.extend(
        build_nat_rule_commands(
            rule_number,
            source_nat_iface,
            source_network,
            identity,
        )
    )


@interfaces_bp.route("/interfaces/create", methods=["POST"])
@login_required
def create_vlan():
    data = request.get_json()
    parent = data.get("parent")
    vlan_id = data.get("vlan_id")
    description = data.get("description")
    address = data.get("address")
    mode = (data.get("mode") or "static").strip().lower()
    source_nat_iface = (data.get("source_nat_interface") or "").strip()
    zone_field = data.get("zone")
    zone_name = sanitise_zone_name(zone_field) if zone_field is not None else None

    if not parent or not vlan_id:
        return {"status": "error", "message": "Missing parent or VLAN ID"}, 400
    if mode not in {"dhcp", "static"}:
        return {"status": "error", "message": "Mode must be either DHCP or Static."}, 400
    if source_nat_iface and not source_nat_iface.startswith("eth"):
        return {"status": "error", "message": "Source NAT interface must be an ethernet interface (e.g. eth0)."}, 400

    if mode == "dhcp":
        address = "dhcp"
    elif mode == "static" and address:
        if not is_valid_cidr(address):
            return {"status": "error", "message": "Static VLANs require a valid CIDR address."}, 400
    elif mode == "static" and not address:
        return {"status": "error", "message": "Static VLANs require an address."}, 400
    if source_nat_iface and mode != "static":
        return {"status": "error", "message": "Source NAT requires a static address."}, 400
    if zone_field is not None and zone_field != "" and not zone_name:
        return {"status": "error", "message": "Zone assignment is required."}, 400

    try:
        base_path = ["interfaces", "ethernet", parent, "vif", str(vlan_id)]
        commands = _build_base_interface_commands(base_path, description, address)

        if mode == "static" and address:
            _augment_with_services(commands, address, description, f"{parent}.{vlan_id}")

        if source_nat_iface:
            _append_nat_commands(commands, address, source_nat_iface, f"{parent}.{vlan_id}")

        zone_config_snapshot = load_zone_config()
        commands.extend(build_zone_definition_commands(zone_name, zone_config_snapshot))
        commands.extend(build_zone_membership_commands(zone_name, f"{parent}.{vlan_id}"))

        deduped_commands = _dedupe(commands)

        if current_app:
            current_app.logger.info("VLAN create payload %s: %s", f"{parent}.{vlan_id}", deduped_commands)
        else:
            print("VLAN create payload", f"{parent}.{vlan_id}", deduped_commands)

        success, error_message = configure_set(deduped_commands, error_context=f"VLAN {parent}.{vlan_id}")
        if not success:
            return {"status": "error", "message": error_message}, 500
        return {"status": "ok", "vlan": f"{parent}.{vlan_id}"}
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}, 400
    except Exception as exc:
        return {"status": "error", "message": str(exc)}, 500


@interfaces_bp.route("/interfaces/add", methods=["POST"])
@login_required
def add_interface():
    data = request.get_json() or {}
    iface = (data.get("interface") or "").strip()
    description = (data.get("description") or "").strip()
    address = (data.get("address") or "").strip()
    mode = (data.get("mode") or "static").strip().lower()
    source_nat_iface = (data.get("source_nat_interface") or "").strip()
    zone_field = data.get("zone")
    zone_name = sanitise_zone_name(zone_field) if zone_field is not None else None

    if not iface:
        return {"status": "error", "message": "Interface name is required."}, 400

    if "." in iface or "@" in iface:
        return {"status": "error", "message": "Only base ethernet interfaces can be added here."}, 400

    if not iface.startswith("eth"):
        return {"status": "error", "message": "Interface must be an ethernet interface (e.g. eth0)."}, 400

    if mode not in {"dhcp", "static"}:
        return {"status": "error", "message": "Mode must be either DHCP or Static."}, 400
    if source_nat_iface and not source_nat_iface.startswith("eth"):
        return {"status": "error", "message": "Source NAT interface must be an ethernet interface (e.g. eth0)."}, 400

    if mode == "dhcp":
        address = "dhcp"
    elif mode == "static":
        if not address:
            return {"status": "error", "message": "Static interfaces require an address."}, 400
        if not is_valid_cidr(address):
            return {"status": "error", "message": "Address must be valid CIDR (e.g. 192.168.0.1/24)."}, 400
    if source_nat_iface and mode != "static":
        return {"status": "error", "message": "Source NAT requires a static address."}, 400
    if zone_field is not None and zone_field != "" and not zone_name:
        return {"status": "error", "message": "Zone assignment is required."}, 400

    config_data = current_app.device.retrieve_show_config(path=["interfaces"])
    configured_names = extract_configured_interfaces(getattr(config_data, "result", {}))

    if iface in configured_names:
        return {"status": "error", "message": f"{iface} is already configured."}, 400

    base_path = ["interfaces", "ethernet", iface]

    try:
        commands = _build_base_interface_commands(base_path, description, address)

        if mode == "static" and address:
            _augment_with_services(commands, address, description, iface)

        if source_nat_iface:
            _append_nat_commands(commands, address, source_nat_iface, iface)

        zone_config_snapshot = load_zone_config()
        if zone_name:
            commands.extend(build_zone_definition_commands(zone_name, zone_config_snapshot))
            commands.extend(build_zone_membership_commands(zone_name, iface))

        deduped_commands = _dedupe(commands)

        if current_app:
            current_app.logger.info("Interface create payload %s: %s", iface, deduped_commands)
        else:
            print("Interface create payload", iface, deduped_commands)

        success, error_message = configure_set(deduped_commands, error_context=f"interface {iface}")
        if not success:
            return {"status": "error", "message": error_message}, 500
        return {"status": "ok", "iface": iface}
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}, 400
    except Exception as exc:
        return {"status": "error", "message": str(exc)}, 500


@interfaces_bp.route("/interfaces/delete/<iface>", methods=["POST"])
@login_required
def interfaces_delete(iface):
    try:
        commands: List[List[str]] = []
        zone_config_snapshot = load_zone_config()
        if "@" in iface:
            vlan_id = iface.split("@")[0].split(".")[1]
            parent_interface = iface.split("@")[1]
            iface_path = ["interfaces", "ethernet", parent_interface, "vif", vlan_id]
            commands.append(iface_path)
            commands.append(iface_path + ["description"])
            commands.append(["interfaces", "ethernet", parent_interface, "vif", vlan_id, "address"])
        else:
            iface_path = ["interfaces", "ethernet", iface]
            commands.append(iface_path)
            commands.append(iface_path + ["description"])
            commands.append(iface_path + ["address"])

        config_data = current_app.device.retrieve_show_config(path=["interfaces"])
        config_map = flatten_interface_config(getattr(config_data, "result", {}))
        iface_lookup_key = iface.split("@")[0] if "@" in iface else iface
        iface_details = config_map.get(iface_lookup_key, {})
        shared_name = iface_details.get("description")
        iface_address = iface_details.get("address")
        iface_network = load_cidr_network(iface_address)

        if shared_name:
            commands.append(["service", "dhcp-server", "shared-network-name", shared_name])

        _, listen_ip, allow_from = build_dns_paths(iface_address)
        if listen_ip:
            commands.append(["service", "dns", "forwarding", "listen-address", listen_ip])
        if allow_from:
            commands.append(["service", "dns", "forwarding", "allow-from", allow_from])

        nat_rules = load_nat_source_rules()
        nat_rule_number, _ = find_nat_rule_for_iface(nat_rules, iface_lookup_key, iface_network)
        removed_nat_rule = False
        if nat_rule_number is not None:
            commands.append(["nat", "source", "rule", str(nat_rule_number)])
            removed_nat_rule = True

        existing_zone = find_zone_for_interface(iface_lookup_key, zone_config_snapshot)
        if existing_zone:
            commands.extend(build_zone_membership_delete(existing_zone, iface_lookup_key))

        deduped = _dedupe(commands)

        if current_app:
            current_app.logger.info("Deleting %s with payload: %s", iface, deduped)

        response = current_app.device.configure_delete(path=deduped)
        if getattr(response, "error", None):
            return {"status": "error", "message": response.error}, 500
        if getattr(response, "status", 200) != 200:
            return {"status": "error", "message": f"Device returned status {response.status}"}, 500

        if removed_nat_rule:
            reorder_success, reorder_error = reorder_managed_nat_rules()
            if not reorder_success:
                return {"status": "error", "message": reorder_error}, 500

        return {"status": "ok", "iface": iface}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}, 500

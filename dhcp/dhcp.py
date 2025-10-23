import ipaddress
import json
from flask import Blueprint, render_template, current_app, request, jsonify
from auth_utils import login_required

dhcp_bp = Blueprint('dhcp', __name__)


def _parse_name_servers(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [item.strip() for item in str(value).split(',') if item.strip()]


def _ensure_success(response, action, ignore_missing=False):
    if response is None:
        raise RuntimeError(f"{action}: no response from device")

    error_val = response.error
    if error_val in (None, "", False):
        if response.status and int(response.status) >= 400:
            raise RuntimeError(f"{action}: HTTP status {response.status}")
        return

    message = str(error_val).strip()
    if ignore_missing and message:
        lowered = message.lower()
        for token in ("not exist", "does not exist", "not found", "is not set", "cannot delete"):
            if token in lowered:
                return

    raise RuntimeError(
        f"{action}: {message or 'unknown error'} "
        f"(status={response.status}, result={response.result}, request={response.request})"
    )


def _configure_set(device, path):
    if path and isinstance(path[0], list):
        action = "set (batch)"
    else:
        action = f"set {' '.join(path)}"
    resp = device.configure_set(path=path)
    _ensure_success(resp, action)
    return resp


def _configure_delete(device, path, ignore_missing=False):
    if path and isinstance(path[0], list):
        action = "delete (batch)"
    else:
        action = f"delete {' '.join(path)}"
    resp = device.configure_delete(path=path)
    _ensure_success(resp, action, ignore_missing=ignore_missing)
    return resp


def _commit_changes(device):
    resp = device._api_request(command="configure", op='commit', path=[], method="POST")
    try:
        _ensure_success(resp, "commit configuration")
    except RuntimeError as exc:
        if "nothing to commit" not in str(exc).lower():
            raise
    return resp


def _apply_dhcp_configuration(device, shared_name, subnet, values, subnet_id=None, replace=False):
    base_path = ["service", "dhcp-server", "shared-network-name", shared_name]
    subnet_path = base_path + ["subnet", subnet]

    if replace:
        _configure_delete(
            device,
            [
                subnet_path + ["lease"],
                subnet_path + ["range"],
                subnet_path + ["option", "default-router"],
                subnet_path + ["option", "domain-name"],
                subnet_path + ["option", "name-server"],
                subnet_path + ["subnet-id"],
            ],
            ignore_missing=True,
        )

    default_router = (values.get("defaultRouter") or "").strip()
    domain_name = (values.get("domainName") or "").strip()
    lease = str(values.get("lease") or "").strip()
    start = (values.get("startAddress") or "").strip()
    end = (values.get("endAddress") or "").strip()
    name_servers = _parse_name_servers(values.get("nameServer"))
    enabled_raw = values.get("enabled", True)
    if isinstance(enabled_raw, str):
        enabled = enabled_raw.lower() not in {"false", "0", "no", "off"}
    else:
        enabled = bool(enabled_raw)

    set_paths = []

    if default_router:
        set_paths.append(subnet_path + ["option", "default-router", default_router])
    if domain_name:
        set_paths.append(subnet_path + ["option", "domain-name", domain_name])

    for server in name_servers:
        set_paths.append(subnet_path + ["option", "name-server", server])

    if lease:
        set_paths.append(subnet_path + ["lease", lease])

    if start:
        set_paths.append(subnet_path + ["range", "0", "start", start])
    if end:
        set_paths.append(subnet_path + ["range", "0", "stop", end])

    if subnet_id is None:
        subnet_id = values.get("subnetId")
    if subnet_id:
        set_paths.append(subnet_path + ["subnet-id", str(subnet_id)])

    if enabled:
        delete_disable = True
    else:
        delete_disable = False
        set_paths.append(base_path + ["disable"])

    if set_paths:
        _configure_set(device, set_paths)

    if delete_disable:
        _configure_delete(device, base_path + ["disable"], ignore_missing=True)


def _normalize_payload(payload):
    enabled_raw = payload.get("enabled")
    if isinstance(enabled_raw, str):
        enabled_norm = enabled_raw.lower() not in {"false", "0", "no", "off"}
    else:
        enabled_norm = bool(enabled_raw)

    return {
        "sharedNetwork": (payload.get("sharedNetwork") or "").strip(),
        "subnet": (payload.get("subnet") or "").strip(),
        "defaultRouter": (payload.get("defaultRouter") or "").strip(),
        "nameServer": tuple(_parse_name_servers(payload.get("nameServer"))),
        "domainName": (payload.get("domainName") or "").strip(),
        "lease": str(payload.get("lease") or "").strip(),
        "startAddress": (payload.get("startAddress") or "").strip(),
        "endAddress": (payload.get("endAddress") or "").strip(),
        "subnetId": str(payload.get("subnetId") or "").strip(),
        "enabled": enabled_norm,
    }


def get_next_subnet_id(device):
    data = device.show(path=["configuration", "json"])
    config = json.loads(data.result)
    dhcp_config = config.get("service", {}).get("dhcp-server", {}).get("shared-network-name", {})

    used_ids = set()
    for shared_info in dhcp_config.values():
        for details in shared_info.get("subnet", {}).values():
            try:
                used_ids.add(int(details.get("subnet-id", 0)))
            except (TypeError, ValueError):
                continue

    candidate = 1
    while candidate in used_ids:
        candidate += 1
    return candidate


def _get_interface_details(config, iface):
    ethernet = config.get("interfaces", {}).get("ethernet", {})
    description = ""
    addresses = []

    if iface in ethernet:
        iface_config = ethernet.get(iface, {})
        description = iface_config.get("description", "")
        addresses = iface_config.get("address", [])
    else:
        if "." in iface:
            parent, vlan_id = iface.split(".", 1)
            parent_cfg = ethernet.get(parent, {})
            vif = parent_cfg.get("vif", {}).get(vlan_id, {})
            description = vif.get("description", "")
            addresses = vif.get("address", [])
    return description, addresses


def _get_interface_ip(addresses):
    for addr in addresses:
        if "/" in addr:
            try:
                return str(ipaddress.ip_interface(addr).ip)
            except ValueError:
                continue
    return ""


@dhcp_bp.route('/dhcp')
@login_required
def dhcp():
    data = current_app.device.show(path=["configuration", "json"])
    config = json.loads(data.result)

    interfaces = {}
    ethernet = config.get("interfaces", {}).get("ethernet", {})
    for iface, info in ethernet.items():
        interfaces[iface] = {
            "description": info.get("description", ""),
            "address": info.get("address", []),
        }
        for vlan_id, vlan_info in info.get("vif", {}).items():
            vlan_name = f"{iface}.{vlan_id}"
            interfaces[vlan_name] = {
                "description": vlan_info.get("description", ""),
                "address": vlan_info.get("address", []),
                "parent": iface,
            }

    next_subnet_id = get_next_subnet_id(current_app.device)
    return render_template('dhcp.html', interfaces=interfaces, next_subnet_id=next_subnet_id)


@dhcp_bp.route('/services/dhcp/<iface>', methods=['GET'])
@login_required
def get_dhcp(iface):
    device = current_app.device
    data = device.show(path=["configuration", "json"])
    config = json.loads(data.result)

    dhcp_config = (
        config.get("service", {})
        .get("dhcp-server", {})
        .get("shared-network-name", {})
    )

    description, addresses = _get_interface_details(config, iface)
    interface_ip = _get_interface_ip(addresses)

    def to_subnet(addr):
        if "/" not in addr:
            return None
        try:
            return str(ipaddress.ip_network(addr, strict=False))
        except ValueError:
            return None

    iface_subnets = [to_subnet(addr) for addr in addresses if addr]
    iface_subnets = [s for s in iface_subnets if s]

    matched = None
    for shared_name, shared_info in dhcp_config.items():
        is_disabled = "disable" in shared_info
        for subnet, details in shared_info.get("subnet", {}).items():
            if subnet in iface_subnets:
                matched = {
                    "enabled": not is_disabled,
                    "is_configured": True,
                    "shared_network_name": shared_name,
                    "subnet": subnet,
                    "default_router": details.get("option", {}).get("default-router", ""),
                    "name_server": ", ".join(details.get("option", {}).get("name-server", [])),
                    "domain_name": details.get("option", {}).get("domain-name", ""),
                    "lease": str(details.get("lease", "")),
                    "start": details.get("range", {}).get("0", {}).get("start", ""),
                    "end": details.get("range", {}).get("0", {}).get("stop", ""),
                    "subnet_id": str(details.get("subnet-id", "")),
                }
                break
        if matched:
            break

    if not matched:
        matched = {
            "enabled": False,
            "is_configured": False,
            "shared_network_name": description or iface,
            "subnet": iface_subnets[0] if iface_subnets else "",
            "default_router": interface_ip,
            "name_server": "",
            "domain_name": "vyos.net",
            "lease": "86400",
            "start": "",
            "end": "",
            "subnet_id": "",
        }
    else:
        if not matched.get("default_router") and interface_ip:
            matched["default_router"] = interface_ip

    matched["interface_description"] = description
    matched["interface_ip"] = interface_ip
    matched["next_available_subnet_id"] = str(get_next_subnet_id(device))

    return matched


def _validate_payload(data):
    required = [
        "sharedNetwork",
        "subnet",
        "defaultRouter",
        "nameServer",
        "domainName",
        "lease",
        "startAddress",
        "endAddress",
    ]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")


@dhcp_bp.route('/services/dhcp/<iface>/create', methods=['POST'])
@login_required
def create_dhcp(iface):
    payload = request.get_json() or {}
    data = payload.get("data", payload)

    try:
        _validate_payload(data)
        existing = get_dhcp(iface)
        if existing.get("is_configured"):
            return jsonify({
                "status": "error",
                "message": "DHCP configuration already exists for this interface."
            }), 400

        subnet_id = data.get("subnetId") or existing.get("next_available_subnet_id") or get_next_subnet_id(current_app.device)
        data["subnetId"] = subnet_id

        _apply_dhcp_configuration(
            current_app.device,
            shared_name=data["sharedNetwork"].strip(),
            subnet=data["subnet"].strip(),
            values=data,
            subnet_id=subnet_id,
            replace=True
        )
        _commit_changes(current_app.device)

        refreshed = get_dhcp(iface)
        return jsonify({"status": "ok", "created": True, "data": refreshed})
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@dhcp_bp.route('/services/dhcp/<iface>/update', methods=['POST'])
@login_required
def update_dhcp(iface):
    payload = request.get_json() or {}
    data = payload.get("data", payload)
    original = payload.get("original", {})

    try:
        _validate_payload(data)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    try:
        existing = get_dhcp(iface)
        if not existing.get("is_configured"):
            return jsonify({
                "status": "error",
                "message": "No DHCP configuration exists for this interface."
            }), 400

        existing_payload = {
            "sharedNetwork": existing.get("shared_network_name", ""),
            "subnet": existing.get("subnet", ""),
            "defaultRouter": existing.get("default_router", ""),
            "nameServer": existing.get("name_server", ""),
            "domainName": existing.get("domain_name", ""),
            "lease": existing.get("lease", ""),
            "startAddress": existing.get("start", ""),
            "endAddress": existing.get("end", ""),
            "subnetId": existing.get("subnet_id", ""),
            "enabled": existing.get("enabled", False),
        }

        normalized_new = _normalize_payload(data)
        normalized_existing = _normalize_payload(existing_payload)
        normalized_original = _normalize_payload({
            "sharedNetwork": original.get("sharedNetwork", existing_payload["sharedNetwork"]),
            "subnet": original.get("subnet", existing_payload["subnet"]),
        })

        changes = {
            key: value
            for key, value in normalized_new.items()
            if value != normalized_existing.get(key)
        }

        if not changes:
            refreshed = get_dhcp(iface)
            return jsonify({"status": "ok", "created": False, "data": refreshed})

        device = current_app.device
        old_shared = normalized_original["sharedNetwork"] or normalized_existing["sharedNetwork"]
        old_subnet = normalized_original["subnet"] or normalized_existing["subnet"]
        new_shared = normalized_new["sharedNetwork"]
        new_subnet = normalized_new["subnet"]
        subnet_id = normalized_new["subnetId"] or normalized_existing["subnetId"] or str(get_next_subnet_id(device))
        data["subnetId"] = subnet_id

        if "sharedNetwork" in changes or "subnet" in changes:
            _apply_dhcp_configuration(
                device,
                shared_name=new_shared,
                subnet=new_subnet,
                values=data,
                subnet_id=subnet_id,
                replace=True
            )
            _commit_changes(device)

            old_base = ["service", "dhcp-server", "shared-network-name", old_shared]
            old_subnet_path = old_base + ["subnet", old_subnet]
            _configure_delete(device, old_subnet_path, ignore_missing=True)
            _configure_delete(device, old_base, ignore_missing=True)
            _commit_changes(device)
        else:
            _apply_dhcp_configuration(
                device,
                shared_name=old_shared,
                subnet=old_subnet,
                values=data,
                subnet_id=subnet_id,
                replace=True
            )
            _commit_changes(device)

        refreshed = get_dhcp(iface)
        return jsonify({"status": "ok", "created": False, "data": refreshed})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

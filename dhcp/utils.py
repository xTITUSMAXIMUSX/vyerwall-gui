import ipaddress
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence


def ensure_dict(node: Any) -> Dict[Any, Any]:
    if isinstance(node, dict):
        return node
    if isinstance(node, list):
        merged: Dict[Any, Any] = {}
        for entry in node:
            if isinstance(entry, dict):
                merged.update(entry)
        return merged
    return {}


def ensure_list(node: Any) -> List[Any]:
    if node is None:
        return []
    if isinstance(node, list):
        return list(node)
    if isinstance(node, dict):
        return [str(key) for key in node.keys()]
    return [node]


def dedupe_paths(paths: Iterable[Sequence[str]]) -> List[List[str]]:
    deduped: List[List[str]] = []
    seen = set()
    for path in paths:
        key = tuple(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(list(path))
    return deduped


def strip_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip()


def parse_option_values(option_container: Any, key: str) -> List[str]:
    container = ensure_dict(option_container)
    values = container.get(key)
    if values is None:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    if isinstance(values, dict):
        results: List[str] = []
        for entry_key, entry_val in values.items():
            if isinstance(entry_val, (list, dict)):
                nested = ensure_list(entry_val)
                results.extend(str(item).strip() for item in nested if str(item).strip())
            else:
                results.append(str(entry_key).strip())
                if entry_val not in (None, "", {}):
                    results.append(str(entry_val).strip())
        return [value for value in results if value]
    return [str(values).strip()]


def parse_vendor_options(option_container: Any) -> List[Dict[str, str]]:
    container = ensure_dict(option_container)
    vendor_container = ensure_dict(container.get("vendor-option"))
    results: List[Dict[str, str]] = []
    for name, value in vendor_container.items():
        option_name = str(name).strip()
        if not option_name:
            continue
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                token = str(sub_key).strip()
                if token:
                    results.append({
                        "name": option_name,
                        "value": str(sub_value).strip() if sub_value not in (None, "") else "",
                    })
        elif isinstance(value, list):
            for entry in value:
                entry_val = str(entry).strip()
                if entry_val:
                    results.append({"name": option_name, "value": entry_val})
        else:
            results.append({"name": option_name, "value": str(value).strip()})
    return results


def parse_dynamic_dns(block: Any) -> Dict[str, Any]:
    options = ensure_dict(block)
    if not options:
        return {}

    result: Dict[str, Any] = {}
    simple_keys = {
        "send_updates": "send-updates",
        "override_no_update": "override-no-update",
        "override_client_update": "override-client-update",
        "update_on_renew": "update-on-renew",
        "conflict_resolution": "conflict-resolution",
        "replace_client_name": "replace-client-name",
        "generated_prefix": "generated-prefix",
        "qualifying_suffix": "qualifying-suffix",
        "ttl_percent": "ttl-percent",
        "hostname_char_set": "hostname-char-set",
        "hostname_char_replacement": "hostname-char-replacement",
    }
    for key, option_key in simple_keys.items():
        if option_key in options:
            result[key] = strip_or_none(options.get(option_key))

    tsig_container = ensure_dict(options.get("tsig-key"))
    tsig_keys = []
    for name, details in tsig_container.items():
        entry = {"name": str(name).strip()}
        detail_map = ensure_dict(details)
        if "algorithm" in detail_map:
            entry["algorithm"] = strip_or_none(detail_map.get("algorithm"))
        if "secret" in detail_map:
            entry["secret"] = strip_or_none(detail_map.get("secret"))
        tsig_keys.append(entry)
    if tsig_keys:
        result["tsig_keys"] = tsig_keys

    def _parse_domain_container(domain_container: Any) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        dom_map = ensure_dict(domain_container)
        for domain, details in dom_map.items():
            detail_map = ensure_dict(details)
            entry: Dict[str, Any] = {"domain": str(domain).strip()}
            if "key-name" in detail_map:
                entry["key_name"] = strip_or_none(detail_map.get("key-name"))
            servers: List[Dict[str, str]] = []
            server_map = ensure_dict(detail_map.get("dns-server"))
            for server_id, server_details in server_map.items():
                server_entry: Dict[str, str] = {"id": str(server_id).strip()}
                server_detail_map = ensure_dict(server_details)
                if "address" in server_detail_map:
                    server_entry["address"] = strip_or_none(server_detail_map.get("address")) or ""
                if "port" in server_detail_map:
                    server_entry["port"] = strip_or_none(server_detail_map.get("port")) or ""
                servers.append(server_entry)
            if servers:
                entry["servers"] = servers
            parsed.append(entry)
        return parsed

    forward_domains = _parse_domain_container(options.get("forward-domain"))
    if forward_domains:
        result["forward_domains"] = forward_domains

    reverse_domains = _parse_domain_container(options.get("reverse-domain"))
    if reverse_domains:
        result["reverse_domains"] = reverse_domains

    return result


def parse_high_availability(block: Any) -> Dict[str, Any]:
    settings = ensure_dict(block)
    if not settings:
        return {}

    result = {}
    simple_fields = ["mode", "status", "source-address", "remote", "name"]
    for field in simple_fields:
        if field in settings:
            result[field] = strip_or_none(settings.get(field))
    return result


def parse_lease_table(raw: Any) -> List[Dict[str, str]]:
    if isinstance(raw, dict):
        entries = raw.get("leases") or raw.get("data") or raw.get("dhcp-server")
        if isinstance(entries, list):
            normalized = []
            for lease in entries:
                if not isinstance(lease, dict):
                    continue
                normalized.append({
                    "ip": strip_or_none(lease.get("ip-address")) or strip_or_none(lease.get("ip")) or "",
                    "mac": strip_or_none(lease.get("hardware-address")) or strip_or_none(lease.get("mac")) or "",
                    "state": strip_or_none(lease.get("state")) or "",
                    "lease_start": strip_or_none(lease.get("lease-start")) or strip_or_none(lease.get("start")) or "",
                    "lease_expiration": strip_or_none(lease.get("lease-expiration")) or strip_or_none(lease.get("end")) or "",
                    "remaining": strip_or_none(lease.get("remain")) or strip_or_none(lease.get("remaining")) or "",
                    "pool": strip_or_none(lease.get("pool")) or "",
                    "hostname": strip_or_none(lease.get("hostname")) or "",
                    "origin": strip_or_none(lease.get("origin")) or "",
                })
            return normalized

    text = str(raw or "")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    header_index = None
    for idx, line in enumerate(lines):
        if line.lower().startswith("ip address"):
            header_index = idx
            break
    if header_index is None:
        return []

    leases = []
    for line in lines[header_index + 1:]:
        if set(line.strip()) <= {"-"}:
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 2:
            continue
        entry = {
            "ip": parts[0],
            "mac": parts[1] if len(parts) > 1 else "",
            "state": parts[2] if len(parts) > 2 else "",
            "lease_start": parts[3] if len(parts) > 3 else "",
            "lease_expiration": parts[4] if len(parts) > 4 else "",
            "remaining": parts[5] if len(parts) > 5 else "",
            "pool": parts[6] if len(parts) > 6 else "",
            "hostname": parts[7] if len(parts) > 7 else "",
            "origin": parts[8] if len(parts) > 8 else "",
        }
        leases.append(entry)
    return leases


def get_next_subnet_id(device) -> int:
    data = device.show(path=["configuration", "json"])
    config = json.loads(data.result)
    dhcp_config = (
        config.get("service", {})
        .get("dhcp-server", {})
        .get("shared-network-name", {})
    )

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


def get_interface_details(config: Dict[str, Any], iface: str) -> Dict[str, Any]:
    # Config is already the interfaces result, so get ethernet directly
    ethernet = config.get("ethernet", {})
    description = ""
    addresses: List[str] = []

    if iface in ethernet:
        iface_config = ethernet.get(iface, {})
        description = iface_config.get("description", "")
        addr_value = iface_config.get("address", [])
        # Ensure addresses is always a list
        addresses = addr_value if isinstance(addr_value, list) else [addr_value] if addr_value else []
    else:
        if "." in iface:
            parent, vlan_id = iface.split(".", 1)
            parent_cfg = ethernet.get(parent, {})
            vif = parent_cfg.get("vif", {}).get(vlan_id, {})
            description = vif.get("description", "")
            addr_value = vif.get("address", [])
            # Ensure addresses is always a list
            addresses = addr_value if isinstance(addr_value, list) else [addr_value] if addr_value else []

    return {
        "description": description,
        "addresses": addresses,
    }


def get_interface_ip(addresses: Iterable[str]) -> str:
    for addr in addresses:
        if "/" in addr:
            try:
                return str(ipaddress.ip_interface(addr).ip)
            except ValueError:
                continue
    return ""

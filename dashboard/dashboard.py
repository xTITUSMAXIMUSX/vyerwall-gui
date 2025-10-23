import json
import re
from typing import Optional
from flask import Blueprint, render_template, current_app
from auth_utils import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/get-cpu-usage')
@login_required
def get_cpu_usage():
    data = current_app.device.show(["system", "processes", "extensive"]) # type: ignore
    output = data.result

    for line in output.splitlines():
        if line.strip().startswith("%Cpu(s):"):
            # Extract all floating-point numbers
            numbers = re.findall(r"[\d.]+", line)
            if len(numbers) >= 8:
                # According to the order: us, sy, ni, id, wa, hi, si, st
                idle = float(numbers[3])
                total_used = 100.0 - idle
                total = round(total_used, 1)
    cpu_result = {"cpu_total": total}
    return cpu_result

def parse_size_to_bytes(value: str) -> Optional[float]:
    match = re.match(r"([\d.]+)\s*([A-Za-z]+)?", value)
    if not match:
        return None

    try:
        number = float(match.group(1))
    except ValueError:
        return None
    unit = match.group(2).lower() if match.group(2) else ""

    unit_multipliers = {
        "b": 1,
        "kb": 10**3,
        "k": 10**3,
        "mb": 10**6,
        "m": 10**6,
        "gb": 10**9,
        "g": 10**9,
        "tb": 10**12,
        "t": 10**12,
        "pb": 10**15,
        "p": 10**15,
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
        "tib": 1024**4,
        "pib": 1024**5,
    }

    multiplier = unit_multipliers.get(unit, 1)
    return number * multiplier


def calc_percentage(used_str: str, total_str: str) -> Optional[float]:
    used_bytes = parse_size_to_bytes(used_str)
    total_bytes = parse_size_to_bytes(total_str)

    if used_bytes is None or total_bytes is None:
        return None

    if total_bytes == 0:
        return None

    percentage = (used_bytes / total_bytes) * 100
    return max(0, min(round(percentage, 1), 100))


def fetch_storage_stats():
    data = current_app.device.show(path=["system", "storage"])

    filesystem = size = used = available = "N/A"

    for line in data.result.splitlines():
        if line.startswith("Filesystem:"):
            filesystem = line.split(":", 1)[1].strip()
        elif line.startswith("Size:"):
            size = line.split(":", 1)[1].strip()
        elif line.startswith("Used:"):
            used = line.split(":", 1)[1].strip()
        elif line.startswith("Available:"):
            available = line.split(":", 1)[1].strip()

    return {
        "filesystem": filesystem,
        "size": size,
        "used": used,
        "available": available,
        "percent_used": calc_percentage(used, size)
    }


def fetch_memory_stats():
    data = current_app.device.show(path=["system", "memory"])

    total_memory = used_memory = free_memory = "N/A"

    for line in data.result.splitlines():
        if line.startswith("Total:"):
            total_memory = line.split(":", 1)[1].strip()
        elif line.startswith("Used:"):
            used_memory = line.split(":", 1)[1].strip()
        elif line.startswith("Free:"):
            free_memory = line.split(":", 1)[1].strip()

    return {
        "total_memory": total_memory,
        "used_memory": used_memory,
        "free_memory": free_memory,
        "percent_used": calc_percentage(used_memory, total_memory)
    }


@dashboard_bp.route('/get-memory-usage')
@login_required
def get_memory_usage():
    return fetch_memory_stats()


@dashboard_bp.route('/get-storage-usage')
@login_required
def get_storage_usage():
    return fetch_storage_stats()


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    storage_result = fetch_storage_stats()
    memory_result = fetch_memory_stats()

    # Service Information
    data = current_app.device.show(path=["configuration", "json"])

    config = json.loads(data.result)

    service = config.get("service", {})

    service_names = list(service.keys())


    # Interfaces Information
    data = current_app.device.show(path=["configuration", "json"])

    interfaces = config.get('interfaces', {}).get('ethernet', {})

    # Flatten VLANs into the same dict for easy display
    flat_interfaces = {}

    for iface_name, iface_data in interfaces.items():
        # Add the parent interface
        flat_interfaces[iface_name] = {
            "address": iface_data.get("address", ["N/A"]),
            "description": iface_data.get("description", "N/A")
        }

        # If VLANs (vif) exist, add them too
        if "vif" in iface_data:
            for vlan_id, vlan_data in iface_data["vif"].items():
                vlan_name = f"{iface_name}.{vlan_id}"  # e.g. eth1.5
                flat_interfaces[vlan_name] = {
                    "address": vlan_data.get("address", ["N/A"]),
                    "description": vlan_data.get("description", "N/A")
                }

    return render_template('dashboard.html', storage_result=storage_result, 
                                            memory_result=memory_result,  
                                            service_names=service_names,
                                            interfaces=flat_interfaces)

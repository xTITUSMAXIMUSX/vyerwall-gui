import json
import re
from typing import Optional
from datetime import datetime
from flask import Blueprint, render_template, current_app, jsonify
from app.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/get-cpu-usage')
@login_required
def get_cpu_usage():
    try:
        data = current_app.device.show(["system", "processes", "extensive"]) # type: ignore
        output = data.result

        total = 0.0  # Default value

        for line in output.splitlines():
            # Look for the CPU line: %Cpu(s): 50.0 us,  0.0 sy,  0.0 ni, 50.0 id, ...
            if line.strip().startswith("%Cpu(s):"):
                # Extract all floating-point numbers
                numbers = re.findall(r"[\d.]+", line)

                if len(numbers) >= 4:
                    # Standard top format: us, sy, ni, id, wa, hi, si, st
                    # Index: 0=us, 1=sy, 2=ni, 3=id, 4=wa, 5=hi, 6=si, 7=st
                    idle = float(numbers[3])
                    total_used = 100.0 - idle
                    total = round(max(0.0, min(100.0, total_used)), 1)
                    break

        return {"cpu_total": total}
    except Exception as e:
        # Return 0 if there's any error
        return {"cpu_total": 0.0}

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


def fetch_system_info():
    """Fetch system overview information"""
    try:
        # Get hostname
        hostname_data = current_app.device.show(path=["host", "name"])
        hostname = hostname_data.result.strip() if hostname_data.result else "Unknown"

        # Get version
        version_data = current_app.device.show(path=["version"])
        version_lines = version_data.result.splitlines()
        version = "Unknown"
        for line in version_lines:
            if "Version:" in line:
                version = line.split("Version:", 1)[1].strip()
                break

        # Get uptime
        uptime_data = current_app.device.show(path=["uptime"])
        uptime = uptime_data.result.strip() if uptime_data.result else "Unknown"

        # Get load average from processes
        load_data = current_app.device.show(["system", "processes", "extensive"])
        load_avg = "N/A"
        for line in load_data.result.splitlines():
            if "load average:" in line.lower():
                parts = line.split("load average:", 1)
                if len(parts) > 1:
                    load_avg = parts[1].strip()
                    break

        return {
            "hostname": hostname,
            "version": version,
            "uptime": uptime,
            "load_average": load_avg,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "hostname": "Error",
            "version": "N/A",
            "uptime": "N/A",
            "load_average": "N/A",
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


def fetch_network_traffic():
    """Fetch network interface statistics"""
    try:
        data = current_app.device.show(path=["interfaces"])
        lines = data.result.splitlines()

        interfaces = []
        current_iface = None

        for line in lines:
            line = line.strip()
            if line.startswith("eth") or line.startswith("lo"):
                parts = line.split()
                if len(parts) >= 1:
                    current_iface = {
                        "name": parts[0].rstrip(':'),
                        "rx_bytes": "0",
                        "tx_bytes": "0",
                        "rx_packets": "0",
                        "tx_packets": "0",
                        "rx_errors": "0",
                        "tx_errors": "0"
                    }
                    interfaces.append(current_iface)
            elif current_iface and "RX:" in line:
                parts = line.split()
                if len(parts) >= 3:
                    current_iface["rx_bytes"] = parts[1]
                    current_iface["rx_packets"] = parts[2] if len(parts) > 2 else "0"
            elif current_iface and "TX:" in line:
                parts = line.split()
                if len(parts) >= 3:
                    current_iface["tx_bytes"] = parts[1]
                    current_iface["tx_packets"] = parts[2] if len(parts) > 2 else "0"

        return interfaces
    except Exception as e:
        return []


def fetch_dhcp_leases():
    """Fetch DHCP lease information"""
    try:
        data = current_app.device.show(path=["dhcp", "server", "leases"])
        lines = data.result.splitlines()

        active_leases = 0
        recent_leases = []

        for line in lines:
            if "IP address" in line or "lease for" in line.lower():
                active_leases += 1
                if len(recent_leases) < 5:
                    parts = line.split()
                    if len(parts) >= 2:
                        recent_leases.append({
                            "ip": parts[0] if parts[0] != "IP" else parts[2],
                            "info": line
                        })

        return {
            "active_count": active_leases,
            "recent": recent_leases
        }
    except Exception as e:
        return {
            "active_count": 0,
            "recent": []
        }


def fetch_firewall_activity():
    """Fetch firewall statistics and connections"""
    try:
        # Get connection tracking statistics
        conntrack_data = current_app.device.show(path=["conntrack", "table", "ipv4"])
        connections = conntrack_data.result.splitlines()
        active_connections = len([l for l in connections if l.strip()])

        # Try to get firewall statistics
        try:
            fw_stats_data = current_app.device.show(path=["firewall", "statistics"])
            fw_stats = fw_stats_data.result
        except:
            fw_stats = "No statistics available"

        return {
            "active_connections": active_connections,
            "recent_blocks": [],  # Would need log parsing
            "statistics": fw_stats
        }
    except Exception as e:
        return {
            "active_connections": 0,
            "recent_blocks": [],
            "statistics": "N/A"
        }


def fetch_recent_logs():
    """Fetch recent system logs"""
    try:
        log_data = current_app.device.show(path=["log", "tail"])
        lines = log_data.result.splitlines()

        logs = []
        for line in lines[-10:]:  # Last 10 lines
            if line.strip():
                # Determine severity based on keywords
                severity = "info"
                if "error" in line.lower() or "fail" in line.lower():
                    severity = "error"
                elif "warn" in line.lower():
                    severity = "warning"

                logs.append({
                    "message": line.strip(),
                    "severity": severity
                })

        return logs
    except Exception as e:
        return []


@dashboard_bp.route('/api/system-info')
@login_required
def get_system_info():
    return jsonify(fetch_system_info())


@dashboard_bp.route('/api/network-traffic')
@login_required
def get_network_traffic():
    return jsonify(fetch_network_traffic())


@dashboard_bp.route('/api/dhcp-leases')
@login_required
def get_dhcp_leases():
    return jsonify(fetch_dhcp_leases())


@dashboard_bp.route('/api/firewall-activity')
@login_required
def get_firewall_activity():
    return jsonify(fetch_firewall_activity())


@dashboard_bp.route('/api/recent-logs')
@login_required
def get_recent_logs():
    return jsonify(fetch_recent_logs())


@dashboard_bp.route('/api/quick-action/reboot', methods=['POST'])
@login_required
def quick_action_reboot():
    try:
        current_app.device.configure_set(path=["system", "reboot", "now"])
        return jsonify({"status": "ok", "message": "System reboot initiated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    storage_result = fetch_storage_stats()
    memory_result = fetch_memory_stats()
    system_info = fetch_system_info()
    network_traffic = fetch_network_traffic()
    dhcp_leases = fetch_dhcp_leases()
    firewall_activity = fetch_firewall_activity()
    recent_logs = fetch_recent_logs()

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

    return render_template('dashboard.html',
                          storage_result=storage_result,
                          memory_result=memory_result,
                          system_info=system_info,
                          network_traffic=network_traffic,
                          dhcp_leases=dhcp_leases,
                          firewall_activity=firewall_activity,
                          recent_logs=recent_logs,
                          service_names=service_names,
                          interfaces=flat_interfaces)

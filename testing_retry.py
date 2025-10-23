import os
import urllib3
import time
import requests
from pyvyos import VyDevice
from dotenv import load_dotenv
load_dotenv()
urllib3.disable_warnings()

hostname = os.getenv('VYDEVICE_HOSTNAME')
apikey = os.getenv('VYDEVICE_APIKEY')
port = int(os.getenv('VYDEVICE_PORT', '443'))
protocol = os.getenv('VYDEVICE_PROTOCOL', 'https')
verify_ssl = os.getenv('VYDEVICE_VERIFY_SSL')
verify = verify_ssl.lower() == "true" if verify_ssl else True

device = VyDevice(hostname=hostname, apikey=apikey, port=port, protocol=protocol, verify=verify, timeout=2)

sharednetworkname = "TEST2"
subnet = "10.33.33.0/24"
defaultrouter = "10.33.33.1"
nameserver = "10.33.33.1"
domainname = "vyos.net"
lease = "86400"
rangestart = "10.33.33.2"
rangestop = "10.33.33.12"
subnetid = "3"

paths = [
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router", defaultrouter],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server", nameserver],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "domain-name", domainname],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "lease", lease],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "start", rangestart],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "stop", rangestop],
    ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "subnet-id", subnetid],
]

try:
    resp = device.configure_set(path=paths)
    print("configure_set status:", resp.status)
    print("configure_set error:", resp.error)
except Exception as exc:
    print("Exception from configure_set:", repr(exc))

print("Attempting direct request (should fail without network access)...")
url = f"{protocol}://{hostname}:{port}/configure"
headers = {}
payload = {
    'data': '[{"op": "set", "path": ["service", "dhcp-server", "shared-network-name", "TEST2", "subnet", "10.33.33.0/24", "lease", "86400" ]}]',
    'key': apikey
}
try:
    r = requests.post(url, data=payload, timeout=2, verify=verify)
    print("Direct POST status:", r.status_code)
    print("Direct POST body:", r.text[:200])
except Exception as direct_exc:
    print("Direct POST exception:", repr(direct_exc))

print("Finished test")

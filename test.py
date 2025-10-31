import os
from pyvyos import VyDevice
from dotenv import load_dotenv
load_dotenv()

hostname = os.getenv('VYDEVICE_HOSTNAME')
apikey = os.getenv('VYDEVICE_APIKEY')
port = os.getenv('VYDEVICE_PORT')
protocol = os.getenv('VYDEVICE_PROTOCOL')
verify_ssl = os.getenv('VYDEVICE_VERIFY_SSL')

verify = verify_ssl.lower() == "true" if verify_ssl else True

# Initialize VyDevice and store in app context
device = VyDevice(hostname=hostname, apikey=apikey, port=port, protocol=protocol, verify=verify)

data = device.retrieve_show_config(path=["service", "dhcp-server", "shared-network-name", "TEST7"])

print(data.result)

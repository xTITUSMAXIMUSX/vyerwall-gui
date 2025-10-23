import os
import os
import urllib3
import json
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

device = VyDevice(hostname=hostname, apikey=apikey, port=port, protocol=protocol, verify=verify)

payload = ['firewall', 'zone', 'DMZ']

data2 = device.configure_set(path=payload)   

print(data2)
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import urllib3
urllib3.disable_warnings()

from auth_utils import login_required
from pyvyos import VyDevice
from dotenv import load_dotenv
load_dotenv()

hostname = os.getenv('VYDEVICE_HOSTNAME')
apikey = os.getenv('VYDEVICE_APIKEY')
port = os.getenv('VYDEVICE_PORT')
protocol = os.getenv('VYDEVICE_PROTOCOL')
verify_ssl = os.getenv('VYDEVICE_VERIFY_SSL')

verify = verify_ssl.lower() == "true" if verify_ssl else True

# Routes
from dashboard.dashboard import dashboard_bp
from interfaces.interfaces import interfaces_bp
from logs.logs import logs_bp
from dhcp.dhcp import dhcp_bp
from firewall import rules_bp

app = Flask(__name__)
app.secret_key = "supersecretkey" 

# Initialize VyDevice and store in app context
device = VyDevice(hostname=hostname, apikey=apikey, port=port, protocol=protocol, verify=verify)
app.device = device 

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(interfaces_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(dhcp_bp)
app.register_blueprint(rules_bp)

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple check against user
        if username == os.getenv('USERNAME') and password == os.getenv('PASSWORD'):
            session['user'] = username  # store user in session
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash("Invalid username or password.", "error")

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

"""
VyerWall GUI - Main application entry point

A web-based management interface for VyOS firewalls.
"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import urllib3

urllib3.disable_warnings()

from dotenv import load_dotenv
from app.pyvyos import VyDevice

# Load environment variables
load_dotenv()

hostname = os.getenv('VYDEVICE_HOSTNAME')
apikey = os.getenv('VYDEVICE_APIKEY')
port = os.getenv('VYDEVICE_PORT')
protocol = os.getenv('VYDEVICE_PROTOCOL')
verify_ssl = os.getenv('VYDEVICE_VERIFY_SSL')

verify = verify_ssl.lower() == "true" if verify_ssl else True

# Import blueprints
from app.modules.dashboard import dashboard_bp
from app.modules.interfaces import interfaces_bp
from app.modules.logs import logs_bp
from app.modules.dhcp import dhcp_bp
from app.modules.firewall import rules_bp, zone_bp
from app.core import config_bp, is_config_dirty
from app.modules.nat import nat_bp

# Create Flask application
app = Flask(
    __name__,
    template_folder='app/templates',
    static_folder='app/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Context processor to make config status available to all templates
@app.context_processor
def inject_config_status():
    return dict(config_dirty=is_config_dirty())

# Initialize VyDevice and store in app context
device = VyDevice(
    hostname=hostname,
    apikey=apikey,
    port=port,
    protocol=protocol,
    verify=verify
)
app.device = device

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(interfaces_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(dhcp_bp)
app.register_blueprint(rules_bp)
app.register_blueprint(zone_bp)
app.register_blueprint(config_bp)
app.register_blueprint(nat_bp)


@app.route('/')
def index():
    """Redirect to dashboard or login."""
    if 'user' in session:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple check against environment variables
        if username == os.getenv('USERNAME') and password == os.getenv('PASSWORD'):
            session['user'] = username
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash("Invalid username or password.", "error")

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    """Handle user logout."""
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

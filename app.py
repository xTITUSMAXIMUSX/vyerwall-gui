from flask_migrate import Migrate
from models import db, User, APISettings
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app, sessions
from pyvyos.device import VyDevice, ApiResponse
import string
import re
import random
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Routes
from networking.interfaces import bp_interfaces
from networking.vlans import bp_vlans
from services.service_ssh import bp_ssh_service
from services.service_dhcp import bp_dhcp_service
from services.service_dns import bp_dns_service
from firewall.groups import bp_groups


app = Flask(__name__)
# app.register_blueprint(interfaces)
app.secret_key = 'your_secret_key'


# Configure the database URI with mysqlclient
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)
migrate = Migrate(app, db)

# Register Blueprints
app.register_blueprint(bp_interfaces)
app.register_blueprint(bp_vlans)
app.register_blueprint(bp_ssh_service)
app.register_blueprint(bp_dhcp_service)
app.register_blueprint(bp_dns_service)
app.register_blueprint(bp_groups)


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


def get_connected_host():
    connected_host = APISettings.query.filter_by(connected=True).first()
    return connected_host


@app.context_processor
def inject_connected_host():
    connected_host = get_connected_host()
    return dict(connected_host=connected_host)


def create_admin_user():
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        hashed_password = generate_password_hash('admin')
        admin_user = User(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def home():
    return render_template('layouts/main.html')


@app.route('/save-configuration', methods=['POST'])
@login_required
def save_configuration():
    results = current_app.device.config_file_save()
    if results.error == False:
        flash('Configuration saved successfully!', 'success')
    else:
        flash('Something went wrong!', 'error')

    print(results)

    return redirect(request.referrer)


@app.route('/admin')
@login_required
def admin():
    users = User.query.all()
    user_role_forms = {user.id: UserRoleForm(
        prefix=str(user.id)) for user in users}
    return render_template('pages/admin.html', users=users, user_role_forms=user_role_forms)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('api_host'))
            else:
                flash('Invalid username or password. Please try again.', 'error')
        else:
            flash('User does not exist.', category='error')
    return render_template('forms/login.html')


@app.route('/api-host', methods=['GET', 'POST'])
@login_required
def api_host():
    if request.method == 'POST':
        hostname = request.form['hostname']
        apikey = request.form['apikey']
        port = request.form['port']
        protocol = request.form['protocol']
        verify_ssl = request.form.get('verify_ssl', False)

        new_api_host = APISettings(
            hostname=hostname, apikey=apikey, port=port, protocol=protocol, verify_ssl=verify_ssl)

        db.session.add(new_api_host)
        db.session.commit()

    api_entries = APISettings.query.all()
    return render_template('forms/api-host.html', api_entries=api_entries)


@app.route('/edit-api-host/<int:entry_id>', methods=['POST'])
@login_required
def edit_api_host(entry_id):
    if request.method == 'POST':
        entry = APISettings.query.get_or_404(entry_id)

        entry.hostname = request.form.get('hostname')
        entry.apikey = request.form.get('apikey')
        entry.port = request.form.get('port')
        entry.protocol = request.form.get('protocol')
        verify_ssl = request.form.get('verify_ssl')
        if verify_ssl is not None:
            entry.verify_ssl = bool(verify_ssl)
        else:
            entry.verify_ssl = False

        db.session.commit()

        flash('Entry updated successfully.', 'success')
        return redirect(url_for('api_host'))

    return redirect(url_for('api_host'))


@app.route('/connect-api-host/<int:entry_id>', methods=['POST'])
@login_required
def connect_api_host(entry_id):
    connected_host = APISettings.query.filter_by(connected=True).first()
    if connected_host:
        flash('Another API host is already connected. Disconnect it first.', 'error')
        return redirect(url_for('api_host'))

    entry = APISettings.query.get_or_404(entry_id)
    try:
        device = VyDevice(
            hostname=entry.hostname,
            apikey=entry.apikey,
            port=entry.port,
            protocol=entry.protocol,
            verify=entry.verify_ssl
        )
        current_app.device = device  
        entry.connected = True
        db.session.commit()
        flash('Connected to API host successfully.', 'success')
    except Exception as e:
        flash(f'Failed to connect to API host: {str(e)}', 'error')
    return redirect(url_for('home'))

@app.route('/disconnect-api-host/<int:entry_id>', methods=['POST'])
@login_required
def disconnect_api_host(entry_id):
    entry = APISettings.query.get_or_404(entry_id)
    entry.connected = False
    db.session.commit()
    flash('Disconnected from API host successfully.', 'success')
    return redirect(url_for('api_host'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.errorhandler(401)
def unauthorized_access(error):
    return render_template('errors/401.html'), 401

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        create_admin_user()
    app.run(debug=True)

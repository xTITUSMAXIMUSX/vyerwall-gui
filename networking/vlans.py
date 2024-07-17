from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import re
import json

bp_vlans = Blueprint('vlans', __name__)

@bp_vlans.route('/vlans')
@login_required
def vlans():
    response = current_app.device.show([['conf', 'json']])
    load_interfaces = json.loads(response.result)
    interfaces = load_interfaces.get('interfaces', {}).get('ethernet', {})
    vlan_data = []

    for interface_name, interface_details in interfaces.items():
        # Check for VLAN interfaces (vif)
        if 'vif' in interface_details:
            for vif_id, vif_details in interface_details['vif'].items():
                vlan_data.append({
                    'vif': f"{vif_id}",
                    'parentinterface': interface_name,
                    'address': vif_details.get('address', [''])[0],
                    'description': vif_details.get('description', '')
                })

    return render_template('forms/vlans.html', vlan_data=vlan_data)


@bp_vlans.route('/vlans/create', methods=['POST'])
@login_required
def vlans_create():
    parentinterface = request.form.get('parentinterface')
    address = request.form.get('address')
    vlanid = request.form.get('vlanid')
    description = request.form.get('description')

    current_app.device.configure_set(path=[["interfaces", "ethernet", parentinterface, 'vif', vlanid, 'description', description],
                                           ["interfaces", "ethernet", parentinterface, 'vif', vlanid, 'address', address]])
    return redirect(url_for('vlans.vlans'))

@bp_vlans.route('/vlans/delete', methods=['POST'])
@login_required
def vlans_delete():
    parentinterface = request.form.get('parentinterface')
    vif = request.form.get('vif')

    current_app.device.configure_delete(path=[["interfaces", "ethernet", parentinterface, 'vif', vif]])

    return redirect(url_for('vlans.vlans'))
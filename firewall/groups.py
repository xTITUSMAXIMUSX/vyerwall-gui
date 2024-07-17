from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import re
import json

bp_groups = Blueprint('groups', __name__)

@bp_groups.route('/groups')
@login_required
def groups():
    response = current_app.device.show([['conf', 'json']])
    load_groups = json.loads(response.result)
    
    # Network Groups
    network_groups = load_groups.get('firewall', {}).get('group', {}).get('network-group', {})
    network_group_data = []
    
    for group_name, group_details in network_groups.items():
        if 'network' in group_details:
            network_group_data.append({
                'group_name': group_name,
                'network': group_details['network']
            })
    
    # Interface Groups
    interface_groups = load_groups.get('firewall', {}).get('group', {}).get('interface-group', {})
    interface_group_data = []

    for group_name, group_details in interface_groups.items():
        if 'interface' in group_details:
            for interface in group_details['interface']:
                interface_group_data.append({
                    'interface_group_name': group_name,
                    'interface': interface
                })

    # MAC Groups
    mac_groups = load_groups.get('firewall', {}).get('group', {}).get('mac-group', {})
    mac_group_data = {}

    # Collect MAC addresses by group name
    for mac_group_name, mac_group_details in mac_groups.items():
        if 'mac-address' in mac_group_details:
            if mac_group_name not in mac_group_data:
                mac_group_data[mac_group_name] = []
            for mac in mac_group_details['mac-address']:
                mac_group_data[mac_group_name].append(mac)

    # Convert dictionary to list of dictionaries
    mac_group_data_list = [{'mac_group_name': name, 'mac_addresses': macs} for name, macs in mac_group_data.items()]

    return render_template('forms/groups.html', 
                            network_group_data=network_group_data, 
                            interface_group_data=interface_group_data, 
                            mac_group_data=mac_group_data_list)


@bp_groups.route('/groups/network/delete', methods=['POST'])
@login_required
def groups_network_delete():
    group_name = request.form.get('group_name')
    network = request.form.get('network')

    current_app.device.configure_delete(path=[["firewall", "group", "network-group", group_name, 'network', network]])

    return redirect(url_for('groups.groups'))

@bp_groups.route('/groups/network/create', methods=['POST'])
@login_required
def groups_network_create():
    group_name = request.form.get('group_name')
    network = request.form.get('network')

    current_app.device.configure_set(path=[["firewall", "group", "network-group", group_name, 'network', network]])

    return redirect(url_for('groups.groups'))

@bp_groups.route('/groups/interface/create', methods=['POST'])
@login_required
def create_interface_group():
    interface_group_name = request.form.get('group_name')
    interface = request.form.get('interface')
    
    current_app.device.configure_set(path=[["firewall", "group", "interface-group", interface_group_name, 'interface', interface]])
    return redirect(url_for('groups.groups') + '#interface-group-tab')

@bp_groups.route('/groups/interface/delete', methods=['POST'])
@login_required
def delete_interface_group():
    interface_group_name = request.form.get('group_name')
    interface = request.form.get('interface')
    
    current_app.device.configure_delete(path=[["firewall", "group", "interface-group", interface_group_name]])
    return redirect(url_for('groups.groups') + '#interface-group-tab')

@bp_groups.route('/groups/mac/create', methods=['POST'])
@login_required
def create_mac_group():
    mac_group_name = request.form.get('mac_group_name')
    mac = request.form.get('mac')
    
    current_app.device.configure_set(path=[["firewall", "group", "mac-group", mac_group_name, 'mac-address', mac]])
    return redirect(url_for('groups.groups') + '#mac-group-tab')

@bp_groups.route('/groups/mac/add', methods=['POST'])
@login_required
def add_mac_group():
    mac_group_name = request.form.get('mac_group_name_add')
    mac = request.form.get('mac_add')
    
    current_app.device.configure_set(path=[["firewall", "group", "mac-group", mac_group_name, 'mac-address', mac]])
    return redirect(url_for('groups.groups') + '#mac-group-tab')

@bp_groups.route('/groups/mac/remove', methods=['POST'])
@login_required
def remove_mac_group():
    mac_group_name = request.form.get('mac_group_name')
    mac = request.form.get('mac')

    current_app.device.configure_delete(path=[["firewall", "group", "mac-group", mac_group_name, 'mac-address', mac]])
    return redirect(url_for('groups.groups') + '#mac-group-tab')

@bp_groups.route('/groups/mac/delete', methods=['POST'])
@login_required
def delete_mac_group():
    mac_group_name = request.form.get('mac_group_name')
    mac = request.form.get('mac')
    
    current_app.device.configure_delete(path=[["firewall", "group", "mac-group", mac_group_name]])
    return redirect(url_for('groups.groups') + '#mac-group-tab')
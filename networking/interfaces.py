from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import re
import json

bp_interfaces = Blueprint('interfaces', __name__)

@bp_interfaces.route('/interfaces')
@login_required
def interfaces_redirect():
    response = current_app.device.show([['conf', 'json']])
    load_interfaces = json.loads(response.result)
    interfaces = load_interfaces.get('interfaces', {}).get('ethernet', {})
    ethernet_interfaces = []


    for interface_name, interface_details in interfaces.items():
        # Add the main interface
        ethernet_interfaces.append(interface_name)
        # Check for VLAN interfaces (vif)
        if 'vif' in interface_details:
            for vif in interface_details['vif']:
                ethernet_interfaces.append(f"{interface_name}.{vif}")

    if ethernet_interfaces:
        first_interface = ethernet_interfaces[0]
        return redirect(url_for('interfaces.interfaces', selected_interface=first_interface))
    else:
        flash('No Ethernet interfaces found.', 'error')
        return redirect(url_for('home'))

@bp_interfaces.route('/interfaces/<string:selected_interface>')
@login_required
def interfaces(selected_interface):
    try:
        # Make the API call to retrieve the configuration for the selected interface
        if '.' in selected_interface:
            base_interface = selected_interface.split('.')[0]
            vif = selected_interface.split('.')[1]
            interface_ethernet_configuration = current_app.device.retrieve_show_config(path=[["interfaces", "ethernet", base_interface, 'vif', vif]])
            configuration=interface_ethernet_configuration.result
        else:
            interface_ethernet_configuration = current_app.device.retrieve_show_config(path=[["interfaces", "ethernet", selected_interface]])
            configuration=interface_ethernet_configuration.result
        
        response = current_app.device.show([['conf', 'json']])
        load_interfaces = json.loads(response.result)
        interfaces = load_interfaces.get('interfaces', {}).get('ethernet', {})
        ethernet_interfaces = []


        for interface_name, interface_details in interfaces.items():
            # Add the main interface
            ethernet_interfaces.append(interface_name)
            # Check for VLAN interfaces (vif)
            if 'vif' in interface_details:
                for vif in interface_details['vif']:
                    ethernet_interfaces.append(f"{interface_name}.{vif}")

        return render_template('forms/interfaces.html', ethernet_interfaces=ethernet_interfaces,
                                selected_interface=selected_interface,
                                configuration=configuration)
    except Exception as e:
        flash(f'Failed to retrieve configuration for {selected_interface}: {str(e)}', 'error')
        return redirect(url_for('interfaces.interfaces'))

@bp_interfaces.route('/interface/update', methods=['POST'])
@login_required
def interface_configure():
    interface = request.form.get('interface')
    address = request.form.get('address')
    description = request.form.get('description')
    
    current_app.device.configure_delete(path=[["service", "dns", "forwarding"]])

    if '.' in interface:
        base_interface = interface.split('.')[0]
        vif = interface.split('.')[1]
        interface_ethernet_configuration = current_app.device.retrieve_show_config(path=[["interfaces", "ethernet", base_interface, 'vif', vif]])
        current_configuration=interface_ethernet_configuration.result
        current_app.device.configure_delete(path=[["interfaces", "ethernet", base_interface, 'vif', vif]])
        
        if 'address' not in current_configuration:
            current_app.device.configure_set(path=[["interfaces", "ethernet", base_interface, 'vif', vif, "address", address]]) 
        elif address != current_configuration['address']:
            current_app.device.configure_set(path=[["interfaces", "ethernet", base_interface, 'vif', vif,"address", address]])

        if 'description' not in current_configuration:
            current_app.device.configure_set(path=[["interfaces", "ethernet", base_interface, 'vif', vif, "description", description]])
        elif description != current_configuration['description']:
            current_app.device.configure_set(path=[["interfaces", "ethernet", base_interface, 'vif', vif, "description", description]])
            
        return redirect(url_for('interfaces.interfaces', selected_interface=interface))
    else:
        interface_ethernet_configuration = current_app.device.retrieve_show_config(path=[["interfaces", "ethernet", interface]])
        current_configuration=interface_ethernet_configuration.result
        current_app.device.configure_delete(path=[["interfaces", "ethernet", interface]])

        if 'address' not in current_configuration:
            current_app.device.configure_set(path=[["interfaces", "ethernet", interface, "address", address]]) 
        elif address != current_configuration['address']:
            current_app.device.configure_set(path=[["interfaces", "ethernet", interface, "address", address]])

        if 'description' not in current_configuration:
            current_app.device.configure_set(path=[["interfaces", "ethernet", interface, "description", description]])
        elif description != current_configuration['description']:
            current_app.device.configure_set(path=[["interfaces", "ethernet", interface, "description", description]])

        return redirect(url_for('interfaces.interfaces', selected_interface=interface))

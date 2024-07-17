from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

bp_dhcp_service = Blueprint('dhcp_service', __name__)

@bp_dhcp_service.route('/dhcp-service')
def dhcp_redirect():
    dhcp_list = current_app.device.retrieve_show_config(path=[["service", "dhcp-server"]])
    dhcp_result = dhcp_list.result
    if dhcp_result['shared-network-name'].keys() != '':
       shared_network_names = list(dhcp_result['shared-network-name'].keys())
    else:
       shared_network_names = ''
       return redirect(url_for('dhcp_service.dhcp_service_init'))
     
    
    if shared_network_names:
        first_interface = shared_network_names[0]
        return redirect(url_for('dhcp_service.dhcp_service', selected_dhcp=first_interface))
    else:
        flash('No Ethernet interfaces found.', 'error')
        return redirect(url_for('home'))

@bp_dhcp_service.route('/dhcp-service/init')
@login_required
def dhcp_service_init():
    return render_template('forms/dhcp-service-init.html')

@bp_dhcp_service.route('/dhcp-service/<string:selected_dhcp>')
@login_required
def dhcp_service(selected_dhcp):
    dhcp_configuration = current_app.device.retrieve_show_config(path=[["service", "dhcp-server", "shared-network-name", selected_dhcp]])
    selected_dhcp_server = dhcp_configuration.result

    get_dhcp_list = current_app.device.retrieve_show_config(path=[["service", "dhcp-server"]])
    dhcp_result = get_dhcp_list.result

    shared_network_names = list(dhcp_result['shared-network-name'].keys())

    dhcp_config_results = dhcp_configuration.result
    dhcp_subnet = list(dhcp_config_results['subnet'].keys())[0]
    dhcp_lease = dhcp_config_results['subnet'][dhcp_subnet]['lease']
    dhcp_default_router = dhcp_config_results['subnet'][dhcp_subnet]['option']['default-router']
    dhcp_name_server = dhcp_config_results['subnet'][dhcp_subnet]['option']['name-server']
    dhcp_domain_name = dhcp_config_results['subnet'][dhcp_subnet]['option']['domain-name']
    dhcp_range_start = dhcp_config_results['subnet'][dhcp_subnet]['range']['0']['start']
    dhcp_range_stop = dhcp_config_results['subnet'][dhcp_subnet]['range']['0']['stop']
    dhcp_subnet_id = dhcp_config_results['subnet'][dhcp_subnet]['subnet-id']

    dhcp_data = {'subnet': dhcp_subnet, 'lease': dhcp_lease, 'default_router': dhcp_default_router, 
                'name_server': dhcp_name_server, 'domain_name': dhcp_domain_name, 'start_range': dhcp_range_start, 
                'stop_range': dhcp_range_stop, 'subnet_id': dhcp_subnet_id}


    return render_template('forms/dhcp-service.html', shared_network_names=shared_network_names, selected_dhcp=selected_dhcp, dhcp_data=dhcp_data)

@bp_dhcp_service.route('/dhcp-service/update', methods=['POST'])
@login_required
def dhcp_update_service():
    sharednetworkname = request.form.get('sharednetworkname')
    subnet = request.form.get('subnet')
    defaultrouter = request.form.get('defaultrouter')
    nameserver = request.form.get('nameserver')
    domainname = request.form.get('domainname')
    lease = request.form.get('lease')
    rangestart = request.form.get('rangestart')
    rangestop = request.form.get('rangestop')
    subnetid = request.form.get('subnetid')    
    
    current_dhcp_configuration = current_app.device.retrieve_show_config(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname]])
    dhcp_config_results = current_dhcp_configuration.result

    current_dhcp_lease = dhcp_config_results['subnet'][subnet]['lease']
    current_dhcp_default_router = dhcp_config_results['subnet'][subnet]['option']['default-router']
    current_dhcp_name_server = dhcp_config_results['subnet'][subnet]['option']['name-server']
    current_dhcp_domain_name = dhcp_config_results['subnet'][subnet]['option']['domain-name']
    current_dhcp_range_start = dhcp_config_results['subnet'][subnet]['range']['0']['start']
    current_dhcp_range_stop = dhcp_config_results['subnet'][subnet]['range']['0']['stop']
    current_dhcp_subnet_id = dhcp_config_results['subnet'][subnet]['subnet-id']

    # if 'subnet' not in current_configuration or subnet != current_configuration['subnet']:
    #     current_app.device.configure_delete(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server"]])
    #     current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server", nameserver]]) 

    if  nameserver != current_dhcp_name_server:
        current_app.device.configure_delete(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server"]])
        current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server", nameserver]]) 

    if  rangestart != current_dhcp_range_start:
        current_app.device.configure_delete(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "start"]])
        current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "start", rangestart]]) 

    if  defaultrouter != current_dhcp_default_router:
        current_app.device.configure_delete(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router"]])
        current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router", defaultrouter]]) 




    # result = current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router", defaultrouter]
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router", defaultrouter],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server", nameserver],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "domain-name", domainname],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "lease", lease],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "start", rangestart],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "stop", rangestop],
    #                     ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "subnet-id", subnetid]])
    return redirect(url_for('dhcp_service.dhcp_redirect'))

@bp_dhcp_service.route('/dhcp-service/create', methods=['POST'])
@login_required
def dhcp_create_service():
    sharednetworkname = request.form.get('sharednetworkname')
    subnet = request.form.get('subnet')
    defaultrouter = request.form.get('defaultrouter')
    nameserver = request.form.get('nameserver')
    domainname = request.form.get('domainname')
    lease = request.form.get('lease')
    rangestart = request.form.get('rangestart')
    rangestop = request.form.get('rangestop')
    subnetid = request.form.get('subnetid')

    

    result = current_app.device.configure_set(path=[["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "default-router", defaultrouter],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "name-server", nameserver],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "option", "domain-name", domainname],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "lease", lease],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "start", rangestart],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "range", "0", "stop", rangestop],
                        ["service", "dhcp-server", "shared-network-name", sharednetworkname, "subnet", subnet, "subnet-id", subnetid]])
    return redirect(url_for('dhcp_service.dhcp_redirect'))

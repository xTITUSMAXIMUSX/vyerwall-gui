from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

bp_ssh_service = Blueprint('ssh_service', __name__)

@bp_ssh_service.route('/ssh-service')
@login_required
def ssh_service():  
    
    get_service = current_app.device.retrieve_show_config(path=[["service", "ssh"]])
    ssh_service_result = get_service.result

    if 'ssh' in ssh_service_result:
        ssh_status = True
    else:
        ssh_status = False

    return render_template('forms/ssh-service.html', ssh_service_result=ssh_service_result)


@bp_ssh_service.route('/ssh-service/update', methods=['POST'])
@login_required
def ssh_update_service():

    port = request.form.get('port')
    listenaddress = request.form.get('listenaddress')
    ciphers = request.form.get('ciphers')
    macs = request.form.get('macs')
    disablepasswordauth = request.form.get('disablepasswordauth')
    disablehostvalidation = request.form.get('disablehostvalidation')


    current_service_configuration = current_app.device.retrieve_show_config(path=[["service", "ssh"]])
    current_configuration=current_service_configuration.result

    if 'port' not in current_configuration:
        current_app.device.configure_set(path=[["service", "ssh", "port", port]]) 
    elif port != current_configuration['port']:
        current_app.device.configure_set(path=[["service", "ssh", "port", port]]) 
    
    if 'listenaddress' not in current_configuration:
        current_app.device.configure_set(path=[["service", "ssh", "listenaddress", listenaddress]]) 
    elif listenaddress != current_configuration['listenaddress']:
        current_app.device.configure_set(path=[["service", "ssh", "listenaddress", listenaddress]]) 

    flash('SSH service configured successfuly. Don\'t forget to save your changes', 'success')

    return redirect(url_for('ssh_service.ssh_service'))
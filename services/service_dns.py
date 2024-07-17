from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

bp_dns_service = Blueprint('dns_service', __name__)

@bp_dns_service.route('/dns-service')
@login_required
def dns_service():
    dns_configuration = current_app.device.retrieve_show_config(path=[["service", "dns", "forwarding"]])
    selected_dns_server = dns_configuration.result

    if selected_dns_server:
        cachesize = dns_configuration.result['cache-size']
        listenaddress = dns_configuration.result['listen-address']
        allowfrom = dns_configuration.result['allow-from']

        dns_data = {'cachesize': cachesize, 'listenaddress': listenaddress, 'allowfrom': allowfrom}

        return render_template('forms/dns-service.html', dns_data=dns_data)
    else:
        dns_data = {'cachesize': '', 'listenaddress': '', 'allowfrom': ''}
        return render_template('forms/dns-service.html',dns_data=dns_data)


@bp_dns_service.route('/dns-service/create', methods=['POST'])
@login_required
def dns_service_create():
    cachesize = request.form.get('cachesize')
    listenaddress = request.form.get('listenaddress')
    allowfrom = request.form.get('allowfrom')

    current_app.device.configure_set(path=[["service", "dns", "forwarding", 'cache-size', cachesize],
                                            ["service", "dns", "forwarding", 'listen-address', listenaddress],
                                            ["service", "dns", "forwarding", 'allow-from', allowfrom]])
    
    return redirect(url_for('dns_service.dns_service'))


@bp_dns_service.route('/dns-service/update', methods=['POST'])
@login_required
def dns_service_update():
    dns_configuration = current_app.device.retrieve_show_config(path=[["service", "dns", "forwarding"]])
    selected_dns_server = dns_configuration.result

    current_cachesize = dns_configuration.result['cache-size']
    current_listenaddress = list(dns_configuration.result['listen-address'])
    current_allowfrom = dns_configuration.result['allow-from']

    cachesize = request.form.get('cachesize')
    listenaddress = request.form.get('listenaddress')
    allowfrom = request.form.get('allowfrom')

    if  cachesize != current_cachesize or listenaddress != current_listenaddress or allowfrom != current_allowfrom:
        current_app.device.configure_delete(path=[["service", "dns", "forwarding"]])
        current_app.device.configure_set(path=[["service", "dns", "forwarding", 'cache-size', cachesize],
                                                ["service", "dns", "forwarding", 'listen-address', listenaddress],
                                                ["service", "dns", "forwarding", 'cache-size', allowfrom]])

    
    return redirect(url_for('dns_service.dns_service'))


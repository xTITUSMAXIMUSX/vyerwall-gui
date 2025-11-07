"""
Firewall Groups module for managing VyOS firewall groups.
"""
from flask import Blueprint

firewall_groups_bp = Blueprint('firewall_groups', __name__, url_prefix='/firewall/groups')

from . import views

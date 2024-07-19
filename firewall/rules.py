from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
import re
import json

bp_rules = Blueprint('rules', __name__)

@bp_rules.route('/firewall-rules')
@login_required
def rules():
    return render_template('forms/firewall-rules.html')
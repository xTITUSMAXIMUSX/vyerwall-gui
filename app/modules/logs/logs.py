import json
from flask import Blueprint, render_template, current_app
from app.auth import login_required

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs')
@login_required
def logs():
    data = current_app.device.show(path=["system", "logs", "last", "10"])
    raw_output = data.result

    logs = []
    for line in raw_output.splitlines():
        logs.append(line.strip())

    return render_template('logs.html', logs=logs)
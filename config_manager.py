"""
Global configuration management for tracking unsaved changes across the application.
"""
from flask import Blueprint, current_app, jsonify, session, request
from auth_utils import login_required

config_bp = Blueprint("config_manager", __name__, url_prefix="/config")


def mark_config_dirty():
    """Mark that there are unsaved configuration changes."""
    session['config_dirty'] = True
    session.modified = True


def mark_config_clean():
    """Mark that all changes have been saved."""
    session['config_dirty'] = False
    session.modified = True


def is_config_dirty():
    """Check if there are unsaved configuration changes."""
    return session.get('config_dirty', False)


@config_bp.route("/status")
@login_required
def status():
    """Get the current configuration status."""
    return jsonify({
        "status": "ok",
        "dirty": is_config_dirty()
    })


@config_bp.route("/save", methods=["POST"])
@login_required
def save():
    """Save the current configuration to disk."""
    try:
        current_app.device.config_file_save()
        mark_config_clean()
        return jsonify({
            "status": "ok",
            "message": "Configuration saved successfully"
        })
    except Exception as exc:
        current_app.logger.error(f"Failed to save configuration: {exc}")
        return jsonify({
            "status": "error",
            "message": str(exc) or "Failed to save configuration"
        }), 500


@config_bp.route("/discard", methods=["POST"])
@login_required
def discard():
    """Discard unsaved changes (mark as clean without saving)."""
    mark_config_clean()
    return jsonify({
        "status": "ok",
        "message": "Unsaved changes discarded"
    })

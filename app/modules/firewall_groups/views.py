"""
Views for firewall groups management.
"""
from flask import render_template, request, jsonify, current_app
from app.modules.firewall_groups import firewall_groups_bp
from app.modules.firewall_groups.utils import (
    GROUP_TYPES,
    parse_firewall_groups,
    get_all_groups_summary,
    build_group_set_commands,
    build_group_delete_commands,
    validate_group_name,
    validate_member
)
from app.modules.interfaces.device import configure_multiple_op
from app.auth import login_required
from app.core.config_manager import mark_config_dirty


def get_firewall_groups_config():
    """Fetch firewall group configuration from device."""
    try:
        response = current_app.device.retrieve_show_config(path=["firewall", "group"])
        return response.result if hasattr(response, 'result') else {}
    except Exception as e:
        current_app.logger.error(f"Error fetching firewall groups config: {e}")
        return {}


@firewall_groups_bp.route('/')
@login_required
def index():
    """Display firewall groups management page."""
    try:
        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)

        # Calculate statistics
        total_groups = sum(len(groups) for groups in groups_by_type.values())
        stats = {
            'total': total_groups,
            'by_type': {group_type: len(groups) for group_type, groups in groups_by_type.items()}
        }

        return render_template(
            'firewall_groups/index.html',
            active='firewall_groups',
            groups_by_type=groups_by_type,
            group_types=GROUP_TYPES,
            stats=stats
        )
    except Exception as e:
        current_app.logger.error(f"Error loading firewall groups page: {e}")
        return render_template(
            'firewall_groups/index.html',
            active='firewall_groups',
            groups_by_type={},
            group_types=GROUP_TYPES,
            stats={'total': 0, 'by_type': {}},
            error=str(e)
        )


@firewall_groups_bp.route('/api/groups', methods=['GET'])
@login_required
def get_groups():
    """API endpoint to get all firewall groups."""
    try:
        group_type = request.args.get('type')  # Optional filter by type

        config_data = get_firewall_groups_config()

        if group_type and group_type in GROUP_TYPES:
            # Return groups of specific type
            groups_by_type = parse_firewall_groups(config_data)
            groups = groups_by_type.get(group_type, [])
        else:
            # Return all groups
            groups = get_all_groups_summary(config_data)

        return jsonify({
            'status': 'ok',
            'groups': groups
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving firewall groups: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@firewall_groups_bp.route('/api/groups/<group_type>/<group_name>', methods=['GET'])
@login_required
def get_group(group_type, group_name):
    """API endpoint to get a specific firewall group."""
    try:
        if group_type not in GROUP_TYPES:
            return jsonify({
                'status': 'error',
                'message': f'Invalid group type: {group_type}'
            }), 400

        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)

        # Find the specific group
        groups = groups_by_type.get(group_type, [])
        group = next((g for g in groups if g['name'] == group_name), None)

        if not group:
            return jsonify({
                'status': 'error',
                'message': f'Group not found: {group_name}'
            }), 404

        return jsonify({
            'status': 'ok',
            'group': group
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving group {group_type}/{group_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@firewall_groups_bp.route('/api/groups', methods=['POST'])
@login_required
def create_group():
    """API endpoint to create a new firewall group."""
    try:
        data = request.get_json()
        group_type = data.get('type', '').strip()
        group_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        members = data.get('members', [])

        # Validate group type
        if group_type not in GROUP_TYPES:
            return jsonify({
                'status': 'error',
                'message': f'Invalid group type: {group_type}'
            }), 400

        # Validate group name
        is_valid, error_msg = validate_group_name(group_name)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_msg
            }), 400

        # Validate members
        if not members or not isinstance(members, list):
            return jsonify({
                'status': 'error',
                'message': 'At least one member is required'
            }), 400

        # Validate each member
        for member in members:
            is_valid, error_msg = validate_member(group_type, member)
            if not is_valid:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid member "{member}": {error_msg}'
                }), 400

        # Check if group already exists
        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)
        existing_groups = groups_by_type.get(group_type, [])

        if any(g['name'] == group_name for g in existing_groups):
            return jsonify({
                'status': 'error',
                'message': f'Group "{group_name}" already exists'
            }), 409

        # Build and execute set commands
        set_commands = build_group_set_commands(group_type, group_name, members, description)
        operations = [{"op": "set", "path": path} for path in set_commands]

        success, error_message = configure_multiple_op(
            operations,
            error_context=f"create {group_type} {group_name}"
        )

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to create firewall group'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated groups
        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)

        return jsonify({
            'status': 'ok',
            'message': f'Firewall group "{group_name}" created successfully',
            'groups': groups_by_type,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error creating firewall group: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@firewall_groups_bp.route('/api/groups/<group_type>/<group_name>', methods=['PUT'])
@login_required
def update_group(group_type, group_name):
    """API endpoint to update an existing firewall group."""
    try:
        if group_type not in GROUP_TYPES:
            return jsonify({
                'status': 'error',
                'message': f'Invalid group type: {group_type}'
            }), 400

        data = request.get_json()
        new_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        members = data.get('members', [])

        # Validate new name if changing
        if new_name and new_name != group_name:
            is_valid, error_msg = validate_group_name(new_name)
            if not is_valid:
                return jsonify({
                    'status': 'error',
                    'message': error_msg
                }), 400

        # Validate members
        if not members or not isinstance(members, list):
            return jsonify({
                'status': 'error',
                'message': 'At least one member is required'
            }), 400

        for member in members:
            is_valid, error_msg = validate_member(group_type, member)
            if not is_valid:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid member "{member}": {error_msg}'
                }), 400

        operations = []
        name_changed = new_name and new_name != group_name

        if name_changed:
            # Delete old group and create new one with new name
            delete_commands = build_group_delete_commands(group_type, group_name)
            operations.extend([{"op": "delete", "path": path} for path in delete_commands])

            set_commands = build_group_set_commands(group_type, new_name, members, description)
            operations.extend([{"op": "set", "path": path} for path in set_commands])

            error_context = f"rename {group_type} {group_name} to {new_name}"
        else:
            # Just update the existing group (delete and recreate with same name)
            delete_commands = build_group_delete_commands(group_type, group_name)
            operations.extend([{"op": "delete", "path": path} for path in delete_commands])

            set_commands = build_group_set_commands(group_type, group_name, members, description)
            operations.extend([{"op": "set", "path": path} for path in set_commands])

            error_context = f"update {group_type} {group_name}"

        # Execute all operations in a single API call
        success, error_message = configure_multiple_op(operations, error_context=error_context)

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to update firewall group'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated groups
        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)

        return jsonify({
            'status': 'ok',
            'message': f'Firewall group updated successfully',
            'groups': groups_by_type,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error updating firewall group {group_type}/{group_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@firewall_groups_bp.route('/api/groups/<group_type>/<group_name>', methods=['DELETE'])
@login_required
def delete_group(group_type, group_name):
    """API endpoint to delete a firewall group."""
    try:
        if group_type not in GROUP_TYPES:
            return jsonify({
                'status': 'error',
                'message': f'Invalid group type: {group_type}'
            }), 400

        # Build and execute delete operation
        delete_commands = build_group_delete_commands(group_type, group_name)
        operations = [{"op": "delete", "path": path} for path in delete_commands]

        success, error_message = configure_multiple_op(
            operations,
            error_context=f"delete {group_type} {group_name}"
        )

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to delete firewall group'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated groups
        config_data = get_firewall_groups_config()
        groups_by_type = parse_firewall_groups(config_data)

        return jsonify({
            'status': 'ok',
            'message': f'Firewall group "{group_name}" deleted successfully',
            'groups': groups_by_type,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting firewall group {group_type}/{group_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

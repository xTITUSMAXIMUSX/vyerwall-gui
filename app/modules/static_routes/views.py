"""
Views for static routes management.
"""
from flask import render_template, request, jsonify, current_app
from app.modules.static_routes import static_routes_bp
from app.modules.static_routes.utils import (
    parse_static_routes,
    build_route_set_commands,
    build_route_delete_commands,
    validate_route
)
from app.modules.interfaces.device import configure_multiple_op
from app.auth import login_required
from app.core.config_manager import mark_config_dirty


@static_routes_bp.route('/')
@login_required
def index():
    """Display static routes page."""
    try:
        # Retrieve static route configuration
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])

        # Extract data from response
        config_data = config_response.result if hasattr(config_response, 'result') else {}

        # Parse routes
        routes = parse_static_routes(config_data)

        return render_template('static_routes/index.html', routes=routes)
    except Exception as e:
        current_app.logger.error(f"Error loading static routes: {e}")
        return render_template('static_routes/index.html', routes=[], error=str(e))


@static_routes_bp.route('/api/routes', methods=['GET'])
@login_required
def get_routes():
    """API endpoint to get all static routes."""
    try:
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])
        config_data = config_response.result if hasattr(config_response, 'result') else {}

        routes = parse_static_routes(config_data)

        return jsonify({
            'status': 'ok',
            'routes': routes
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving static routes: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@static_routes_bp.route('/api/routes', methods=['POST'])
@login_required
def create_route():
    """API endpoint to create a new static route."""
    try:
        data = request.get_json()
        destination = data.get('destination', '').strip()
        next_hop = data.get('next_hop', '').strip()
        description = data.get('description', '').strip()

        # Validate input
        if not destination or not next_hop:
            return jsonify({
                'status': 'error',
                'message': 'Destination and next-hop are required'
            }), 400

        # Validate route format
        is_valid, error_msg = validate_route(destination, next_hop)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_msg
            }), 400

        # Check if route already exists
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])
        config_data = config_response.result if hasattr(config_response, 'result') else {}
        existing_routes = parse_static_routes(config_data)

        for route in existing_routes:
            if route['destination'] == destination and route['next_hop'] == next_hop:
                return jsonify({
                    'status': 'error',
                    'message': f'Route to {destination} via {next_hop} already exists'
                }), 409

        # Build and execute operations
        set_commands = build_route_set_commands(destination, next_hop, description)
        operations = [{"op": "set", "path": path} for path in set_commands]

        success, error_message = configure_multiple_op(
            operations,
            error_context=f"create static route {destination} via {next_hop}"
        )

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to create static route'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated routes
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])
        config_data = config_response.result if hasattr(config_response, 'result') else {}
        routes = parse_static_routes(config_data)

        return jsonify({
            'status': 'ok',
            'message': 'Static route created successfully',
            'routes': routes,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error creating static route: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@static_routes_bp.route('/api/routes', methods=['PUT'])
@login_required
def update_route():
    """API endpoint to update an existing static route."""
    try:
        data = request.get_json()
        old_destination = data.get('old_destination', '').strip()
        old_next_hop = data.get('old_next_hop', '').strip()
        new_destination = data.get('destination', '').strip()
        new_next_hop = data.get('next_hop', '').strip()
        description = data.get('description', '').strip()

        # Validate input
        if not all([old_destination, old_next_hop, new_destination, new_next_hop]):
            return jsonify({
                'status': 'error',
                'message': 'All route parameters are required'
            }), 400

        # Validate new route format
        is_valid, error_msg = validate_route(new_destination, new_next_hop)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': error_msg
            }), 400

        # Check if route destination/next-hop changed
        route_changed = (old_destination != new_destination) or (old_next_hop != new_next_hop)

        # Combine all operations into a single payload for better performance
        operations = []

        if route_changed:
            # Delete old route and add new route in single payload
            delete_commands = build_route_delete_commands(old_destination, old_next_hop)
            operations.extend([{"op": "delete", "path": path} for path in delete_commands])

            set_commands = build_route_set_commands(new_destination, new_next_hop, description)
            operations.extend([{"op": "set", "path": path} for path in set_commands])

            error_context = f"update static route from {old_destination} via {old_next_hop} to {new_destination} via {new_next_hop}"
        else:
            # Only description changed, just update it
            set_commands = build_route_set_commands(new_destination, new_next_hop, description)
            operations.extend([{"op": "set", "path": path} for path in set_commands])

            error_context = f"update static route description {new_destination} via {new_next_hop}"

        # Execute all operations in a single API call
        success, error_message = configure_multiple_op(operations, error_context=error_context)

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to update static route'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated routes
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])
        config_data = config_response.result if hasattr(config_response, 'result') else {}
        routes = parse_static_routes(config_data)

        return jsonify({
            'status': 'ok',
            'message': 'Static route updated successfully',
            'routes': routes,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error updating static route: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@static_routes_bp.route('/api/routes', methods=['DELETE'])
@login_required
def delete_route():
    """API endpoint to delete a static route."""
    try:
        data = request.get_json()
        destination = data.get('destination', '').strip()
        next_hop = data.get('next_hop', '').strip()

        # Validate input
        if not destination or not next_hop:
            return jsonify({
                'status': 'error',
                'message': 'Destination and next-hop are required'
            }), 400

        # Build and execute delete operation
        delete_commands = build_route_delete_commands(destination, next_hop)
        operations = [{"op": "delete", "path": path} for path in delete_commands]

        success, error_message = configure_multiple_op(
            operations,
            error_context=f"delete static route {destination} via {next_hop}"
        )

        if not success:
            return jsonify({
                'status': 'error',
                'message': error_message or 'Failed to delete static route'
            }), 500

        # Mark config as dirty
        mark_config_dirty()

        # Get updated routes
        config_response = current_app.device.retrieve_show_config(['protocols', 'static'])
        config_data = config_response.result if hasattr(config_response, 'result') else {}
        routes = parse_static_routes(config_data)

        return jsonify({
            'status': 'ok',
            'message': 'Static route deleted successfully',
            'routes': routes,
            'config_dirty': True
        })

    except Exception as e:
        current_app.logger.error(f"Error deleting static route: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

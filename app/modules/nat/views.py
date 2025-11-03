import json
from flask import Blueprint, render_template, request, jsonify, current_app
from app.auth import login_required
from app.core import mark_config_dirty

nat_bp = Blueprint('nat', __name__)


def get_nat_config():
    """Fetch NAT configuration from device"""
    try:
        response = current_app.device.retrieve_show_config(path=["nat"])
        # retrieve_show_config returns a response object, access .result attribute
        return response.result if hasattr(response, 'result') else {}
    except Exception as e:
        print(f"Error fetching NAT config: {e}")
        return {}


def get_next_rule_number(rules_dict):
    """Get the next available rule number"""
    if not rules_dict:
        return "100"

    rule_numbers = [int(num) for num in rules_dict.keys()]
    max_rule = max(rule_numbers)
    return str(max_rule + 1)


def parse_nat_rules(nat_config):
    """Parse NAT configuration into a structured format"""
    rules = []

    # Parse source NAT rules
    source_rules = nat_config.get("source", {}).get("rule", {})
    for rule_num, rule_data in source_rules.items():
        rules.append({
            "rule_number": rule_num,
            "type": "source",
            "description": rule_data.get("description", ""),
            "outbound_interface": rule_data.get("outbound-interface", {}).get("name", ""),
            "source_address": rule_data.get("source", {}).get("address", ""),
            "translation": rule_data.get("translation", {}).get("address", ""),
            "enabled": True  # VyOS doesn't have disabled state in config
        })

    # Parse destination NAT rules (if any)
    destination_rules = nat_config.get("destination", {}).get("rule", {})
    for rule_num, rule_data in destination_rules.items():
        translation_data = rule_data.get("translation", {})

        # Check if it's a redirect (port forwarding to same IP)
        redirect_data = translation_data.get("redirect", {})
        if redirect_data:
            translation_address = "redirect"
            translation_port = redirect_data.get("port", "")
        else:
            translation_address = translation_data.get("address", "")
            translation_port = translation_data.get("port", "")

        rules.append({
            "rule_number": rule_num,
            "type": "destination",
            "description": rule_data.get("description", ""),
            "inbound_interface": rule_data.get("inbound-interface", {}).get("name", ""),
            "destination_address": rule_data.get("destination", {}).get("address", ""),
            "destination_port": rule_data.get("destination", {}).get("port", ""),
            "protocol": rule_data.get("protocol", ""),
            "translation_address": translation_address,
            "translation_port": translation_port,
            "enabled": True
        })

    # Sort by rule number
    rules.sort(key=lambda x: int(x["rule_number"]))

    return rules


def get_available_interfaces():
    """Get list of available network interfaces"""
    try:
        data = current_app.device.show(path=["configuration", "json"])
        config = json.loads(data.result)

        interfaces = []
        ethernet_interfaces = config.get('interfaces', {}).get('ethernet', {})

        for iface_name, iface_data in ethernet_interfaces.items():
            interfaces.append(iface_name)

            # Add VLANs
            if "vif" in iface_data:
                for vlan_id in iface_data["vif"].keys():
                    interfaces.append(f"{iface_name}.{vlan_id}")

        return sorted(interfaces)
    except Exception as e:
        return []


@nat_bp.route('/nat')
@login_required
def nat_page():
    """NAT configuration page"""
    nat_config = get_nat_config()
    rules = parse_nat_rules(nat_config)
    interfaces = get_available_interfaces()

    return render_template('nat/index.html',
                          active='nat',
                          rules=rules,
                          interfaces=interfaces)


@nat_bp.route('/api/nat/rules', methods=['GET'])
@login_required
def get_nat_rules():
    """API endpoint to get NAT rules"""
    nat_config = get_nat_config()
    rules = parse_nat_rules(nat_config)

    return jsonify({"status": "ok", "rules": rules})


@nat_bp.route('/api/nat/rule', methods=['POST'])
@login_required
def create_nat_rule():
    """Create a new NAT rule using configure_multiple_op for single payload"""
    try:
        data = request.json
        rule_type = data.get("type", "source")

        # Get current config to determine next rule number
        nat_config = get_nat_config()

        # Build operations list for batch execution
        operations = []

        if rule_type == "source":
            existing_rules = nat_config.get("source", {}).get("rule", {})
            rule_number = data.get("rule_number") or get_next_rule_number(existing_rules)

            # Build configuration path
            base_path = ["nat", "source", "rule", rule_number]

            # Add description operation
            if data.get("description"):
                operations.append({"op": "set", "path": base_path + ["description", data["description"]]})

            # Add outbound interface operation
            if data.get("outbound_interface"):
                operations.append({"op": "set", "path": base_path + ["outbound-interface", "name", data["outbound_interface"]]})

            # Add source address operation
            if data.get("source_address"):
                operations.append({"op": "set", "path": base_path + ["source", "address", data["source_address"]]})

            # Add translation operation
            translation = data.get("translation", "masquerade")
            operations.append({"op": "set", "path": base_path + ["translation", "address", translation]})

        elif rule_type == "destination":
            existing_rules = nat_config.get("destination", {}).get("rule", {})
            rule_number = data.get("rule_number") or get_next_rule_number(existing_rules)

            # Build configuration path
            base_path = ["nat", "destination", "rule", rule_number]

            # Add description operation
            if data.get("description"):
                operations.append({"op": "set", "path": base_path + ["description", data["description"]]})

            # Add inbound interface operation
            if data.get("inbound_interface"):
                operations.append({"op": "set", "path": base_path + ["inbound-interface", "name", data["inbound_interface"]]})

            # Add destination address operation
            if data.get("destination_address"):
                operations.append({"op": "set", "path": base_path + ["destination", "address", data["destination_address"]]})

            # Add destination port operation
            if data.get("destination_port"):
                operations.append({"op": "set", "path": base_path + ["destination", "port", data["destination_port"]]})

            # Add protocol operation
            if data.get("protocol"):
                operations.append({"op": "set", "path": base_path + ["protocol", data["protocol"]]})

            # Add translation address or redirect operations
            translation_address = data.get("translation_address", "")
            if translation_address.lower() == "redirect":
                # Use redirect (port forwarding to same IP)
                if data.get("translation_port"):
                    operations.append({"op": "set", "path": base_path + ["translation", "redirect", "port", data["translation_port"]]})
            else:
                # Use specific address
                if translation_address:
                    operations.append({"op": "set", "path": base_path + ["translation", "address", translation_address]})
                # Set translation port
                if data.get("translation_port"):
                    operations.append({"op": "set", "path": base_path + ["translation", "port", data["translation_port"]]})

        # Execute all operations in a single API call
        if operations:
            current_app.device.configure_multiple_op(op_path=operations)

        mark_config_dirty()

        # Return updated rules
        nat_config = get_nat_config()
        rules = parse_nat_rules(nat_config)

        return jsonify({"status": "ok", "rules": rules, "config_dirty": True})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def reorder_rules(rule_type):
    """Reorder rules to be sequential starting from 100 using configure_multiple_op"""
    try:
        nat_config = get_nat_config()

        if rule_type == "source":
            existing_rules = nat_config.get("source", {}).get("rule", {})
        else:
            existing_rules = nat_config.get("destination", {}).get("rule", {})

        if not existing_rules:
            return

        # Get all rule numbers sorted
        rule_numbers = sorted([int(num) for num in existing_rules.keys()])

        # Check if reordering is needed
        needs_reorder = False
        for i, num in enumerate(rule_numbers):
            expected = 100 + i
            if num != expected:
                needs_reorder = True
                break

        if not needs_reorder:
            return

        # Store all rules data
        rules_data = [(num, existing_rules[str(num)]) for num in rule_numbers]

        # Build operations list for configure_multiple_op
        operations = []

        # Delete all existing rules
        for num in rule_numbers:
            if rule_type == "source":
                operations.append({"op": "delete", "path": ["nat", "source", "rule", str(num)]})
            else:
                operations.append({"op": "delete", "path": ["nat", "destination", "rule", str(num)]})

        # Recreate rules with sequential numbers
        for i, (old_num, rule_data) in enumerate(rules_data):
            new_num = str(100 + i)

            if rule_type == "source":
                base_path = ["nat", "source", "rule", new_num]

                if rule_data.get("description"):
                    operations.append({"op": "set", "path": base_path + ["description", rule_data["description"]]})

                outbound_iface = rule_data.get("outbound-interface", {}).get("name")
                if outbound_iface:
                    operations.append({"op": "set", "path": base_path + ["outbound-interface", "name", outbound_iface]})

                source_addr = rule_data.get("source", {}).get("address")
                if source_addr:
                    operations.append({"op": "set", "path": base_path + ["source", "address", source_addr]})

                translation_addr = rule_data.get("translation", {}).get("address")
                if translation_addr:
                    operations.append({"op": "set", "path": base_path + ["translation", "address", translation_addr]})

            else:  # destination
                base_path = ["nat", "destination", "rule", new_num]

                if rule_data.get("description"):
                    operations.append({"op": "set", "path": base_path + ["description", rule_data["description"]]})

                inbound_iface = rule_data.get("inbound-interface", {}).get("name")
                if inbound_iface:
                    operations.append({"op": "set", "path": base_path + ["inbound-interface", "name", inbound_iface]})

                dest_addr = rule_data.get("destination", {}).get("address")
                if dest_addr:
                    operations.append({"op": "set", "path": base_path + ["destination", "address", dest_addr]})

                dest_port = rule_data.get("destination", {}).get("port")
                if dest_port:
                    operations.append({"op": "set", "path": base_path + ["destination", "port", dest_port]})

                protocol = rule_data.get("protocol")
                if protocol:
                    operations.append({"op": "set", "path": base_path + ["protocol", protocol]})

                translation_data = rule_data.get("translation", {})
                redirect_data = translation_data.get("redirect", {})

                if redirect_data:
                    redirect_port = redirect_data.get("port")
                    if redirect_port:
                        operations.append({"op": "set", "path": base_path + ["translation", "redirect", "port", redirect_port]})
                else:
                    trans_addr = translation_data.get("address")
                    if trans_addr:
                        operations.append({"op": "set", "path": base_path + ["translation", "address", trans_addr]})

                    trans_port = translation_data.get("port")
                    if trans_port:
                        operations.append({"op": "set", "path": base_path + ["translation", "port", trans_port]})

        # Execute all operations in a single API call
        if operations:
            current_app.device.configure_multiple_op(op_path=operations)

    except Exception as e:
        print(f"Error reordering rules: {e}")


@nat_bp.route('/api/nat/rule/<rule_type>/<rule_number>', methods=['DELETE'])
@login_required
def delete_nat_rule(rule_type, rule_number):
    """Delete a NAT rule and reorder remaining rules"""
    try:
        if rule_type == "source":
            current_app.device.configure_delete(path=["nat", "source", "rule", rule_number])
        elif rule_type == "destination":
            current_app.device.configure_delete(path=["nat", "destination", "rule", rule_number])
        else:
            return jsonify({"status": "error", "message": "Invalid rule type"}), 400

        # Reorder rules to maintain sequential numbering
        reorder_rules(rule_type)

        mark_config_dirty()

        # Return updated rules
        nat_config = get_nat_config()
        rules = parse_nat_rules(nat_config)

        return jsonify({"status": "ok", "rules": rules, "config_dirty": True})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@nat_bp.route('/api/nat/rule/<rule_type>/<rule_number>', methods=['PUT'])
@login_required
def update_nat_rule(rule_type, rule_number):
    """Update an existing NAT rule"""
    try:
        data = request.json

        # Delete the old rule
        if rule_type == "source":
            current_app.device.configure_delete(path=["nat", "source", "rule", rule_number])
        elif rule_type == "destination":
            current_app.device.configure_delete(path=["nat", "destination", "rule", rule_number])

        # Create the updated rule with the same rule number
        data["rule_number"] = rule_number
        data["type"] = rule_type

        # Recreate the rule (reuse create logic)
        if rule_type == "source":
            base_path = ["nat", "source", "rule", rule_number]

            if data.get("description"):
                current_app.device.configure_set(path=base_path + ["description", data["description"]])

            if data.get("outbound_interface"):
                current_app.device.configure_set(path=base_path + ["outbound-interface", "name", data["outbound_interface"]])

            if data.get("source_address"):
                current_app.device.configure_set(path=base_path + ["source", "address", data["source_address"]])

            translation = data.get("translation", "masquerade")
            current_app.device.configure_set(path=base_path + ["translation", "address", translation])

        elif rule_type == "destination":
            base_path = ["nat", "destination", "rule", rule_number]

            if data.get("description"):
                current_app.device.configure_set(path=base_path + ["description", data["description"]])

            if data.get("inbound_interface"):
                current_app.device.configure_set(path=base_path + ["inbound-interface", "name", data["inbound_interface"]])

            if data.get("destination_address"):
                current_app.device.configure_set(path=base_path + ["destination", "address", data["destination_address"]])

            if data.get("destination_port"):
                current_app.device.configure_set(path=base_path + ["destination", "port", data["destination_port"]])

            if data.get("protocol"):
                current_app.device.configure_set(path=base_path + ["protocol", data["protocol"]])

            # Set translation address or redirect
            translation_address = data.get("translation_address", "")
            if translation_address.lower() == "redirect":
                # Use redirect (port forwarding to same IP)
                if data.get("translation_port"):
                    current_app.device.configure_set(path=base_path + ["translation", "redirect", "port", data["translation_port"]])
            else:
                # Use specific address
                if translation_address:
                    current_app.device.configure_set(path=base_path + ["translation", "address", translation_address])
                # Set translation port
                if data.get("translation_port"):
                    current_app.device.configure_set(path=base_path + ["translation", "port", data["translation_port"]])

        mark_config_dirty()

        # Return updated rules
        nat_config = get_nat_config()
        rules = parse_nat_rules(nat_config)

        return jsonify({"status": "ok", "rules": rules, "config_dirty": True})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@nat_bp.route('/api/nat/reorder/<rule_type>', methods=['POST'])
@login_required
def reorder_nat_rules(rule_type):
    """Reorder NAT rules based on new order using configure_multiple_op"""
    try:
        data = request.json
        rules_data = data.get("rules", [])  # List of full rule objects in new order

        print(f"[NAT REORDER] Received request for {rule_type}")
        print(f"[NAT REORDER] Received {len(rules_data)} rules to reorder")

        if rule_type not in ["source", "destination"]:
            return jsonify({"status": "error", "message": "Invalid rule type"}), 400

        if not rules_data:
            return jsonify({"status": "error", "message": "No rules provided"}), 400

        # Get current configuration to get the rule numbers we need to delete
        nat_config = get_nat_config()
        if rule_type == "source":
            existing_rules = nat_config.get("source", {}).get("rule", {})
        else:
            existing_rules = nat_config.get("destination", {}).get("rule", {})

        print(f"[NAT REORDER] Existing rules in VyOS: {list(existing_rules.keys())}")

        # Build operations list for configure_multiple_op
        operations = []

        # Delete all existing rules
        for rule_num in existing_rules.keys():
            if rule_type == "source":
                operations.append({"op": "delete", "path": ["nat", "source", "rule", rule_num]})
            else:
                operations.append({"op": "delete", "path": ["nat", "destination", "rule", rule_num]})

        # Recreate rules with sequential numbers in new order
        for i, rule_data in enumerate(rules_data):
            new_num = str(100 + i)

            if rule_type == "source":
                base_path = ["nat", "source", "rule", new_num]

                if rule_data.get("description"):
                    operations.append({"op": "set", "path": base_path + ["description", rule_data["description"]]})

                outbound_iface = rule_data.get("outbound_interface")
                if outbound_iface:
                    operations.append({"op": "set", "path": base_path + ["outbound-interface", "name", outbound_iface]})

                source_addr = rule_data.get("source_address")
                if source_addr:
                    operations.append({"op": "set", "path": base_path + ["source", "address", source_addr]})

                translation_addr = rule_data.get("translation")
                if translation_addr:
                    operations.append({"op": "set", "path": base_path + ["translation", "address", translation_addr]})

            else:  # destination
                base_path = ["nat", "destination", "rule", new_num]

                if rule_data.get("description"):
                    operations.append({"op": "set", "path": base_path + ["description", rule_data["description"]]})

                inbound_iface = rule_data.get("inbound_interface")
                if inbound_iface:
                    operations.append({"op": "set", "path": base_path + ["inbound-interface", "name", inbound_iface]})

                dest_addr = rule_data.get("destination_address")
                if dest_addr:
                    operations.append({"op": "set", "path": base_path + ["destination", "address", dest_addr]})

                dest_port = rule_data.get("destination_port")
                if dest_port:
                    operations.append({"op": "set", "path": base_path + ["destination", "port", dest_port]})

                protocol = rule_data.get("protocol")
                if protocol:
                    operations.append({"op": "set", "path": base_path + ["protocol", protocol]})

                # Handle translation (redirect vs specific address) - frontend sends flat structure
                translation_address = rule_data.get("translation_address", "")
                if translation_address.lower() == "redirect":
                    # Redirect: port forward to same IP
                    if rule_data.get("translation_port"):
                        operations.append({"op": "set", "path": base_path + ["translation", "redirect", "port", rule_data["translation_port"]]})
                else:
                    # Translate to specific address
                    if translation_address:
                        operations.append({"op": "set", "path": base_path + ["translation", "address", translation_address]})

                    if rule_data.get("translation_port"):
                        operations.append({"op": "set", "path": base_path + ["translation", "port", rule_data["translation_port"]]})

        # Execute all operations in a single API call
        if operations:
            current_app.device.configure_multiple_op(op_path=operations)

        mark_config_dirty()

        # Return updated rules
        nat_config = get_nat_config()
        rules = parse_nat_rules(nat_config)

        return jsonify({"status": "ok", "rules": rules, "config_dirty": True})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

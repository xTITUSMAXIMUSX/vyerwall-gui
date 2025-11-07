from typing import Dict, Iterable, List, Optional, Tuple

from flask import current_app

from .constants import MIN_NAT_RULE_NUMBER, NAT_RULE_DESCRIPTION_PREFIX, NAT_TRANSLATION_MODE
from .device import configure_set
from .utils import extract_leaf_value, flatten_config_tree, normalise_iface_name, normalise_rule_map

Command = List[str]
CommandList = List[Command]
NatRules = Dict[int, Dict]


def load_nat_source_rules() -> NatRules:
    """Return current NAT source rules as a dict keyed by rule number."""
    nat_result: Dict = {}

    try:
        nat_resp = current_app.device.retrieve_show_config(path=["nat", "source"])
        nat_result = getattr(nat_resp, "result", {}) or {}
    except Exception:
        nat_result = {}

    if not isinstance(nat_result, dict) or "rule" not in nat_result:
        try:
            nat_resp = current_app.device.retrieve_show_config(path=["nat"])
            nat_root = getattr(nat_resp, "result", {}) or {}
            if isinstance(nat_root, dict):
                nat_result = nat_root.get("source", {}) or {}
            else:
                nat_result = {}
        except Exception:
            nat_result = {}

    rule_container = {}
    if isinstance(nat_result, dict):
        rule_container = nat_result.get("rule", {}) or {}

    return normalise_rule_map(rule_container)


def nat_rule_description(iface_name: str) -> str:
    normalised = normalise_iface_name(iface_name) or ""
    return f"{NAT_RULE_DESCRIPTION_PREFIX}{normalised}"


def _is_managed_nat_rule(rule_cfg: Dict) -> bool:
    if not isinstance(rule_cfg, dict):
        return False
    description_value = extract_leaf_value(rule_cfg.get("description"))
    return isinstance(description_value, str) and description_value.startswith(NAT_RULE_DESCRIPTION_PREFIX)


def extract_managed_iface_name(rule_cfg: Dict) -> Optional[str]:
    if not isinstance(rule_cfg, dict):
        return None
    description_value = extract_leaf_value(rule_cfg.get("description"))
    if isinstance(description_value, str) and description_value.startswith(NAT_RULE_DESCRIPTION_PREFIX):
        return description_value[len(NAT_RULE_DESCRIPTION_PREFIX):] or None
    return None


def extract_nat_outbound_interface(rule_cfg: Dict) -> Optional[str]:
    if not isinstance(rule_cfg, dict):
        return None
    outbound = rule_cfg.get("outbound-interface")
    if isinstance(outbound, dict):
        outbound = outbound.get("name")
    return extract_leaf_value(outbound)


def extract_nat_source_network(rule_cfg: Dict) -> Optional[str]:
    if not isinstance(rule_cfg, dict):
        return None
    source = rule_cfg.get("source")
    if isinstance(source, dict):
        source = source.get("address")
    return extract_leaf_value(source)


def build_nat_rule_commands(rule_number: int, outbound_iface: str, source_network: str, iface_name: str) -> CommandList:
    rule = str(rule_number)
    commands: CommandList = [
        ["nat", "source", "rule", rule],
        ["nat", "source", "rule", rule, "outbound-interface", "name", outbound_iface],
        ["nat", "source", "rule", rule, "source", "address", source_network],
        ["nat", "source", "rule", rule, "translation", "address", NAT_TRANSLATION_MODE],
        ["nat", "source", "rule", rule, "description", nat_rule_description(iface_name)],
    ]
    return commands


def build_nat_rule_update_commands(rule_number: int, outbound_iface: str, source_network: str, iface_name: str) -> CommandList:
    rule = str(rule_number)
    return [
        ["nat", "source", "rule", rule, "outbound-interface", "name", outbound_iface],
        ["nat", "source", "rule", rule, "source", "address", source_network],
        ["nat", "source", "rule", rule, "translation", "address", NAT_TRANSLATION_MODE],
        ["nat", "source", "rule", rule, "description", nat_rule_description(iface_name)],
    ]


def find_nat_rule_for_iface(nat_rules: NatRules, iface_name: str, candidate_network: Optional[str] = None) -> Tuple[Optional[int], Optional[Dict]]:
    if not nat_rules:
        return None, None
    normalised = normalise_iface_name(iface_name)
    target_description = nat_rule_description(normalised or "")

    # First, try to find by description (for backward compatibility)
    for rule_number, rule_cfg in nat_rules.items():
        if not isinstance(rule_cfg, dict):
            continue
        description_value = extract_leaf_value(rule_cfg.get("description"))
        if description_value == target_description:
            return rule_number, rule_cfg

    # If not found by description and we have a candidate network,
    # look for a rule with matching source network
    # This allows users to customize descriptions while still cleaning up NAT rules
    if candidate_network:
        for rule_number, rule_cfg in nat_rules.items():
            if not isinstance(rule_cfg, dict):
                continue
            network_value = extract_nat_source_network(rule_cfg)
            if network_value == candidate_network:
                return rule_number, rule_cfg

    return None, None


def next_nat_rule_number(nat_rules: NatRules) -> int:
    if not nat_rules:
        return MIN_NAT_RULE_NUMBER
    max_rule = max(nat_rules.keys())
    return max_rule + 1 if max_rule >= MIN_NAT_RULE_NUMBER else MIN_NAT_RULE_NUMBER


def map_nat_assignments(nat_rules: Optional[NatRules] = None) -> Dict[str, Dict[str, Optional[str]]]:
    rules = nat_rules if nat_rules is not None else load_nat_source_rules()
    assignment: Dict[str, Dict[str, Optional[str]]] = {}
    for rule_number, rule_cfg in rules.items():
        iface_name = extract_managed_iface_name(rule_cfg)
        if not iface_name:
            continue
        outbound_iface = extract_nat_outbound_interface(rule_cfg)
        assignment[iface_name] = {
            "outbound": outbound_iface,
            "rule": rule_number,
            "network": extract_nat_source_network(rule_cfg),
        }
    return assignment


def reorder_managed_nat_rules(nat_rules: Optional[NatRules] = None):
    rules = nat_rules if nat_rules is not None else load_nat_source_rules()
    managed_rules = [
        (rule_number, rule_cfg)
        for rule_number, rule_cfg in sorted(rules.items())
        if _is_managed_nat_rule(rule_cfg)
    ]

    if len(managed_rules) <= 1:
        return True, None

    needs_reorder = any(
        rule_number != MIN_NAT_RULE_NUMBER + index
        for index, (rule_number, _) in enumerate(managed_rules)
    )

    if not needs_reorder:
        return True, None

    delete_paths: CommandList = []
    set_commands: CommandList = []

    for index, (rule_number, rule_cfg) in enumerate(managed_rules):
        new_rule_number = MIN_NAT_RULE_NUMBER + index
        if new_rule_number == rule_number:
            continue
        delete_paths.append(["nat", "source", "rule", str(rule_number)])
        set_commands.extend(
            flatten_config_tree(
                rule_cfg, prefix=["nat", "source", "rule", str(new_rule_number)]
            )
        )

    if delete_paths:
        response = current_app.device.configure_delete(path=delete_paths)
        if getattr(response, "error", None):
            return False, f"Failed to reorder NAT rules: {response.error}"
        status = getattr(response, "status", 200)
        if status != 200:
            return False, f"Device returned status {status} while reordering NAT rules"

    if set_commands:
        success, error_message = configure_set(set_commands, error_context="NAT rule reorder")
        if not success:
            return False, error_message

    return True, None

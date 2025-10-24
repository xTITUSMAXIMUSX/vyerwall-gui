(function initFirewallConstants(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});

  firewallNs.constants = Object.freeze({
    selectors: {
      zoneList: '#firewallZoneList',
      pairList: '#firewallPairList',
      tableBody: '#firewallRulesBody',
      title: '#firewallTitle',
      description: '#firewallDescription',
      defaultAction: '#firewallDefaultAction',
      ruleCount: '#firewallRuleCount',
      zonePair: '#firewallZonePair',
      addRuleButton: '#createFirewallRule',
      reorderControls: '#reorderControls',
      reorderSave: '#reorderSave',
      reorderCancel: '#reorderCancel',
    },
    allowedPortProtocols: Object.freeze(['tcp', 'udp', 'tcp_udp']),
    defaultPortProtocol: 'tcp_udp',
    labels: Object.freeze({
      any: 'Any',
      all: 'All',
      actions: {
        accept: { icon: 'check_circle', className: 'text-green-400', label: 'Accept rule' },
        drop: { icon: 'cancel', className: 'text-amber-400', label: 'Drop rule' },
        reject: { icon: 'do_not_disturb_on', className: 'text-red-500', label: 'Reject rule' },
        fallback: { icon: 'radio_button_unchecked', className: 'text-gray-500', label: 'No action set' },
      },
    }),
  });
})(window);

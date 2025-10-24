(function initFirewallApi(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const utils = firewallNs.utils || {};

  const { encodeName = (name) => encodeURIComponent(name) } = utils;

  async function performRequest(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.status !== 'ok') {
      const message = payload.message || `Request failed with status ${response.status}`;
      throw new Error(message);
    }
    return payload.data;
  }

  function firewallUrl(name, suffix = '') {
    const encoded = encodeName(name);
    return `/firewall/rules/api/names/${encoded}${suffix}`;
  }

  async function fetchFirewallDetails(name) {
    const response = await fetch(firewallUrl(name));
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.status !== 'ok') {
      const message = payload.message || `Unable to load firewall ${name}`;
      throw new Error(message);
    }
    return payload.data;
  }

  function createRule(name, body) {
    return performRequest(firewallUrl(name, '/rules'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  function updateRule(name, ruleNumber, body) {
    return performRequest(firewallUrl(name, `/rules/${encodeURIComponent(ruleNumber)}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  function deleteRule(name, ruleNumber) {
    return performRequest(firewallUrl(name, `/rules/${encodeURIComponent(ruleNumber)}`), {
      method: 'DELETE',
    });
  }

  function toggleRule(name, ruleNumber, disabled) {
    return performRequest(firewallUrl(name, `/rules/${encodeURIComponent(ruleNumber)}/toggle`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disabled }),
    });
  }

  function reorderRules(name, order) {
    return performRequest(firewallUrl(name, '/rules/reorder'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order }),
    });
  }

  firewallNs.api = {
    performRequest,
    fetchFirewallDetails,
    createRule,
    updateRule,
    deleteRule,
    toggleRule,
    reorderRules,
  };
})(window);

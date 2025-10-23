(function initFirewallUtils(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const constants = firewallNs.constants;

  const HTML_ESCAPES = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };

  function normalizeValue(value) {
    return String(value ?? '').trim();
  }

  function isAnyValue(value) {
    const normalized = normalizeValue(value).toLowerCase();
    return normalized === '' || normalized === 'any';
  }

  function isAllProtocol(value) {
    const normalized = normalizeValue(value).toLowerCase();
    return normalized === '' || normalized === 'any' || normalized === 'all';
  }

  function formatProtocolDisplay(value) {
    return isAllProtocol(value) ? constants.labels.all : normalizeValue(value);
  }

  function formatEndpointDisplay(value) {
    return isAnyValue(value) ? constants.labels.any : normalizeValue(value);
  }

  function formatPortDisplay(value) {
    return isAnyValue(value) ? constants.labels.any : normalizeValue(value);
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => HTML_ESCAPES[char] || char);
  }

  function toggleButtonLoading(buttonEl, spinnerEl, labelEl, isLoading, idleText, busyText) {
    if (!buttonEl || !labelEl) {
      return;
    }

    if (isLoading) {
      buttonEl.disabled = true;
      buttonEl.classList.add('opacity-70', 'cursor-not-allowed', 'animate-pulse');
      if (spinnerEl) {
        spinnerEl.classList.remove('hidden');
      }
      labelEl.textContent = busyText;
    } else {
      buttonEl.disabled = false;
      buttonEl.classList.remove('opacity-70', 'cursor-not-allowed', 'animate-pulse');
      if (spinnerEl) {
        spinnerEl.classList.add('hidden');
      }
      labelEl.textContent = idleText;
    }
  }

  function cloneRules(rules) {
    return (rules || []).map((rule) => ({ ...rule }));
  }

  function encodeName(name) {
    return encodeURIComponent(name);
  }

  firewallNs.utils = {
    normalizeValue,
    isAnyValue,
    isAllProtocol,
    formatProtocolDisplay,
    formatEndpointDisplay,
    formatPortDisplay,
    escapeHtml,
    toggleButtonLoading,
    cloneRules,
    encodeName,
  };
})(window);

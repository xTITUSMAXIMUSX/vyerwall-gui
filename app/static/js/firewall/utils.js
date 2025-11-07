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

  function formatGroupDisplay(value, groupsDetails) {
    if (!value) {
      return constants.labels.any || 'Any';
    }

    const valueStr = String(value).trim();

    // Check if this is a group reference: [group:address-group:GROUP_NAME]
    if (valueStr.startsWith('[group:') && valueStr.endsWith(']')) {
      // Extract group type and name
      const groupContent = valueStr.substring(7, valueStr.length - 1); // Remove [group: and ]
      const parts = groupContent.split(':');

      if (parts.length >= 2) {
        const groupType = parts[0];
        const groupName = parts.slice(1).join(':');
        const lookupKey = `${groupType}:${groupName}`;

        // Get members from groupsDetails
        const members = (groupsDetails && groupsDetails[lookupKey]) || [];
        const memberList = members.slice(0, 5).join(', ');
        const moreCount = members.length - 5;
        const tooltipText = memberList + (moreCount > 0 ? ` +${moreCount} more` : '');

        // Return HTML for badge
        return `<span class="inline-flex items-center gap-1 px-2 py-1 bg-purple-500/20 border border-purple-500/40 rounded-md text-purple-300 text-xs font-medium cursor-help group-badge"
                      data-group-type="${escapeHtml(groupType)}"
                      data-group-name="${escapeHtml(groupName)}"
                      data-tooltip="${escapeHtml(tooltipText)}">
                  <span class="material-icons" style="font-size: 14px;">workspaces</span>
                  <span>${escapeHtml(groupName)}</span>
                </span>`;
      }
    }

    // Not a group, return as-is or "Any" if empty
    return isAnyValue(valueStr) ? (constants.labels.any || 'Any') : escapeHtml(valueStr);
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
    formatGroupDisplay,
  };
})(window);

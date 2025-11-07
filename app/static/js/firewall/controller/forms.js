(function initFirewallForms(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const constants = firewallNs.constants || {};
  const utils = firewallNs.utils || {};

  const allowedPortProtocols = constants.allowedPortProtocols || [];
  const defaultPortProtocol = constants.defaultPortProtocol || 'all';

  const {
    normalizeValue = (value) => String(value ?? '').trim(),
    isAnyValue = (value) => normalizeValue(value).length === 0 || normalizeValue(value).toLowerCase() === 'any',
    isAllProtocol = (value) => normalizeValue(value).length === 0 || normalizeValue(value).toLowerCase() === 'all',
  } = utils;

  function getPortControls(form, kind) {
    if (!form) return { select: null, input: null };
    return {
      select: form.querySelector(`[data-port-select="${kind}"]`),
      input: form.querySelector(`[data-port-input="${kind}"]`),
    };
  }

  function setInputReadOnly(input, readOnly) {
    if (!input) return;
    input.readOnly = readOnly;
    input.classList.toggle('opacity-60', readOnly);
    input.classList.toggle('cursor-not-allowed', readOnly);
  }

  function setProtocolValue(form, protocol, options = {}) {
    if (!form) return;
    const select = form.querySelector('select[name="protocol"]');
    if (!select) return;

    let desired = (protocol || '').toLowerCase();
    if (!desired && options.force) {
      desired = defaultPortProtocol;
    }
    if (!desired) return;

    if (options.force && !allowedPortProtocols.includes(desired)) {
      desired = defaultPortProtocol;
    }

    const match = Array.from(select.options).find((opt) => opt.value === desired);
    if (match) {
      select.value = desired;
    }
  }

  function applyPortPreset(form, kind, options = {}) {
    const { select, input } = getPortControls(form, kind);
    if (!select || !input) return;

    if (options.selectValue !== undefined) {
      select.value = options.selectValue;
    }

    const option = select.options[select.selectedIndex];
    if (!option) return;

    if (option.value === 'other') {
      setInputReadOnly(input, false);
      if (options.existingValue !== undefined) {
        input.value = options.preserveInput ? options.existingValue : (options.existingValue || '');
      } else if (!options.preserveInput) {
        input.value = '';
      }
      if (options.protocolOverride) {
        setProtocolValue(form, options.protocolOverride, { force: false });
      }
    } else {
      setInputReadOnly(input, true);
      input.value = option.value;
      const protocol = option.dataset.protocol || options.protocolOverride;
      if (protocol) {
        setProtocolValue(form, protocol, { force: true });
      }
    }
  }

  function setupPortPresets(form, defaultPreset) {
    if (!form) return;
    ['source', 'destination'].forEach((kind) => {
      const controls = getPortControls(form, kind);
      if (!controls.select || !controls.input) return;

      controls.select.addEventListener('change', () => {
        applyPortPreset(form, kind, {
          existingValue: controls.input.value,
          preserveInput: true,
        });
      });

      if (defaultPreset !== undefined) {
        applyPortPreset(form, kind, {
          selectValue: defaultPreset,
          existingValue: controls.input.value,
          protocolOverride: defaultPortProtocol,
          preserveInput: false,
        });
      } else {
        applyPortPreset(form, kind, {
          existingValue: controls.input.value,
          preserveInput: true,
        });
      }
    });
  }

  function applyPresetForRule(form, kind, portValue, protocol) {
    const normalizedProtocol = (protocol || '').toLowerCase();
    const controls = getPortControls(form, kind);
    if (!controls.select) return;

    const options = Array.from(controls.select.options).filter((opt) => opt.value !== 'other');
    const match = options.find((opt) => {
      if (!portValue) return false;
      if (opt.value !== String(portValue)) return false;
      const optProtocol = (opt.dataset.protocol || '').toLowerCase();
      if (!optProtocol || !normalizedProtocol) {
        return true;
      }
      return optProtocol === normalizedProtocol;
    });

    if (match) {
      applyPortPreset(form, kind, {
        selectValue: match.value,
        protocolOverride: match.dataset.protocol || normalizedProtocol,
        preserveInput: false,
      });
    } else {
      applyPortPreset(form, kind, {
        selectValue: 'other',
        existingValue: portValue || '',
        protocolOverride: normalizedProtocol,
        preserveInput: true,
      });
    }
  }

  function computeNextRuleNumber(rules) {
    if (!rules || rules.length === 0) {
      return 100;
    }
    const numbers = rules
      .map((rule) => parseInt(rule.number, 10))
      .filter((value) => Number.isInteger(value));
    if (!numbers.length) {
      return 100;
    }
    return Math.max(...numbers) + 1;
  }

  function resetAddForm(form, rules) {
    if (!form) return;
    form.reset();
    const nextNumber = computeNextRuleNumber(rules);
    if (form.elements.number) {
      form.elements.number.value = nextNumber;
    }
    if (form.elements.protocol) {
      form.elements.protocol.value = defaultPortProtocol;
    }
    applyPortPreset(form, 'source', {
      selectValue: 'other',
      existingValue: '',
      protocolOverride: defaultPortProtocol,
      preserveInput: false,
    });
    applyPortPreset(form, 'destination', {
      selectValue: 'other',
      existingValue: '',
      protocolOverride: defaultPortProtocol,
      preserveInput: false,
    });

    // Reset group toggles to manual entry
    resetGroupToggles(form, '');
  }

  function setupGroupToggles(form, prefix = '') {
    if (!form) return;

    // Setup address toggles (source and destination)
    ['source', 'destination'].forEach((kind) => {
      const typeName = prefix ? `${prefix}${kind.charAt(0).toUpperCase()}${kind.slice(1)}AddressType` : `${kind}AddressType`;
      const radios = form.querySelectorAll(`input[name="${typeName}"]`);

      radios.forEach((radio) => {
        radio.addEventListener('change', () => {
          toggleAddressInput(form, kind, radio.value, prefix);
        });
      });

      // Setup address group select change listener for timeout visibility
      const groupAttr = prefix ? `${prefix}-${kind}-group` : `${kind}-group`;
      const groupSelect = form.querySelector(`[data-address-input="${groupAttr}"]`);
      if (groupSelect) {
        groupSelect.addEventListener('change', () => {
          updateTimeoutVisibility(form, kind, groupSelect, prefix);
        });
      }
    });

    // Setup port toggles (source and destination)
    ['source', 'destination'].forEach((kind) => {
      const typeName = prefix ? `${prefix}${kind.charAt(0).toUpperCase()}${kind.slice(1)}PortType` : `${kind}PortType`;
      const radios = form.querySelectorAll(`input[name="${typeName}"]`);

      radios.forEach((radio) => {
        radio.addEventListener('change', () => {
          togglePortInput(form, kind, radio.value, prefix);
          // When switching to port group, ensure protocol is valid for ports
          if (radio.value === 'group') {
            ensureValidPortProtocol(form);
          }
        });
      });
    });

    // Also listen to port group select changes to ensure protocol is valid
    const portGroupSelects = form.querySelectorAll('select[name="sourcePortGroup"], select[name="destinationPortGroup"]');
    portGroupSelects.forEach((select) => {
      select.addEventListener('change', () => {
        if (select.value) {
          ensureValidPortProtocol(form);
        }
      });
    });
  }

  function ensureValidPortProtocol(form) {
    if (!form) return;
    const protocolSelect = form.elements.protocol;
    if (!protocolSelect) return;

    const currentProtocol = (protocolSelect.value || '').toLowerCase();
    // If current protocol is not valid for ports, set it to default (tcp_udp)
    if (!allowedPortProtocols.includes(currentProtocol)) {
      setProtocolValue(form, defaultPortProtocol, { force: true });
    }
  }

  function toggleAddressInput(form, kind, type, prefix = '') {
    const inputAttr = prefix ? `${prefix}-${kind}-manual` : `${kind}-manual`;
    const groupAttr = prefix ? `${prefix}-${kind}-group` : `${kind}-group`;

    const manualInput = form.querySelector(`[data-address-input="${inputAttr}"]`);
    const groupSelect = form.querySelector(`[data-address-input="${groupAttr}"]`);

    if (type === 'manual') {
      if (manualInput) manualInput.classList.remove('hidden');
      if (groupSelect) groupSelect.classList.add('hidden');
      hideTimeoutContainer(form, kind, prefix);
    } else {
      if (manualInput) manualInput.classList.add('hidden');
      if (groupSelect) groupSelect.classList.remove('hidden');
      updateTimeoutVisibility(form, kind, groupSelect, prefix);
    }
  }

  function hideTimeoutContainer(form, kind, prefix = '') {
    const timeoutAttr = prefix ? `${prefix}-${kind}` : kind;
    const timeoutContainer = form.querySelector(`[data-timeout-container="${timeoutAttr}"]`);
    if (timeoutContainer) {
      timeoutContainer.classList.add('hidden');
    }
  }

  function updateTimeoutVisibility(form, kind, groupSelect, prefix = '') {
    if (!groupSelect) return;

    const timeoutAttr = prefix ? `${prefix}-${kind}` : kind;
    const timeoutContainer = form.querySelector(`[data-timeout-container="${timeoutAttr}"]`);
    if (!timeoutContainer) return;

    const selectedValue = groupSelect.value || '';
    const isDynamicGroup = selectedValue.startsWith('dynamic-group:');

    if (isDynamicGroup) {
      timeoutContainer.classList.remove('hidden');
    } else {
      timeoutContainer.classList.add('hidden');
    }
  }

  function togglePortInput(form, kind, type, prefix = '') {
    const containerAttr = prefix ? `${prefix}-${kind}-manual` : `${kind}-manual`;
    const groupAttr = prefix ? `${prefix}-${kind}-group` : `${kind}-group`;

    const manualContainer = form.querySelector(`[data-port-container="${containerAttr}"]`);
    const groupSelect = form.querySelector(`[data-port-container="${groupAttr}"]`);

    if (type === 'manual') {
      if (manualContainer) manualContainer.classList.remove('hidden');
      if (groupSelect) groupSelect.classList.add('hidden');
    } else {
      if (manualContainer) manualContainer.classList.add('hidden');
      if (groupSelect) groupSelect.classList.remove('hidden');
    }
  }

  function resetGroupToggles(form, prefix = '') {
    if (!form) return;

    // Reset to manual entry for addresses
    ['source', 'destination'].forEach((kind) => {
      const typeName = prefix ? `${prefix}${kind.charAt(0).toUpperCase()}${kind.slice(1)}AddressType` : `${kind}AddressType`;
      const manualRadio = form.querySelector(`input[name="${typeName}"][value="manual"]`);
      if (manualRadio) {
        manualRadio.checked = true;
        toggleAddressInput(form, kind, 'manual', prefix);
      }
    });

    // Reset to manual entry for ports
    ['source', 'destination'].forEach((kind) => {
      const typeName = prefix ? `${prefix}${kind.charAt(0).toUpperCase()}${kind.slice(1)}PortType` : `${kind}PortType`;
      const manualRadio = form.querySelector(`input[name="${typeName}"][value="manual"]`);
      if (manualRadio) {
        manualRadio.checked = true;
        togglePortInput(form, kind, 'manual', prefix);
      }
    });
  }

  function serializeForm(form) {
    const data = new FormData(form);
    const payload = {};
    data.forEach((value, key) => {
      payload[key] = typeof value === 'string' ? value.trim() : value;
    });
    if (form.elements.disabled) {
      payload.disabled = form.elements.disabled.checked;
    }

    // Handle group selections
    // Check if using groups for addresses/ports and include that info in payload
    const sourceAddressType = form.querySelector('input[name="sourceAddressType"]:checked, input[name="editSourceAddressType"]:checked');
    const destinationAddressType = form.querySelector('input[name="destinationAddressType"]:checked, input[name="editDestinationAddressType"]:checked');
    const sourcePortType = form.querySelector('input[name="sourcePortType"]:checked, input[name="editSourcePortType"]:checked');
    const destinationPortType = form.querySelector('input[name="destinationPortType"]:checked, input[name="editDestinationPortType"]:checked');

    if (sourceAddressType && sourceAddressType.value === 'group') {
      payload.sourceAddressType = 'group';
    }
    if (destinationAddressType && destinationAddressType.value === 'group') {
      payload.destinationAddressType = 'group';
    }
    if (sourcePortType && sourcePortType.value === 'group') {
      payload.sourcePortType = 'group';
    }
    if (destinationPortType && destinationPortType.value === 'group') {
      payload.destinationPortType = 'group';
    }

    return payload;
  }

  function normalizePortList(value) {
    if (!value) {
      return undefined;
    }
    const cleaned = value
      .split(',')
      .map((token) => token.trim().replace(/^['"]+|['"]+$/g, ''))
      .filter(Boolean)
      .join(',');
    return cleaned || undefined;
  }

  function normalizePayload(payload, form) {
    const normalized = { ...payload };
    ['sourceAddress', 'destinationAddress', 'description', 'protocol'].forEach((key) => {
      if (normalized[key] === '') {
        normalized[key] = undefined;
      }
    });
    normalized.sourcePort = normalizePortList(normalized.sourcePort);
    normalized.destinationPort = normalizePortList(normalized.destinationPort);

    // Check if using port groups
    const usingSourcePortGroup = normalized.sourcePortType === 'group' && normalized.sourcePortGroup;
    const usingDestinationPortGroup = normalized.destinationPortType === 'group' && normalized.destinationPortGroup;

    // Ports are provided if either manual ports or port groups are used
    const portsProvided = Boolean(normalized.sourcePort) || Boolean(normalized.destinationPort) ||
                          usingSourcePortGroup || usingDestinationPortGroup;

    if (portsProvided) {
      let proto = (normalized.protocol || '').toLowerCase();
      if (!allowedPortProtocols.includes(proto)) {
        normalized.protocol = defaultPortProtocol;
        if (form) {
          setProtocolValue(form, defaultPortProtocol, { force: true });
        }
      } else {
        normalized.protocol = proto;
      }
    }
    if (typeof normalized.disabled === 'undefined') {
      delete normalized.disabled;
    }
    return normalized;
  }

  function populateEditForm(form, rule) {
    if (!form || !rule) return;
    form.elements.originalNumber.value = rule.number;
    form.elements.number.value = rule.number;
    form.elements.action.value = rule.action || 'accept';

    let normalizedProtocol = normalizeValue(rule.protocol).toLowerCase();
    if (isAllProtocol(rule.protocol)) {
      normalizedProtocol = 'all';
    }
    const protocolSelect = form.elements.protocol;
    if (protocolSelect) {
      const availableValues = Array.from(protocolSelect.options).map((opt) => opt.value);
      protocolSelect.value = availableValues.includes(normalizedProtocol) ? normalizedProtocol : '';
    }

    form.elements.description.value = rule.description || '';

    // Handle source address (check for group syntax)
    const sourceAddress = isAnyValue(rule.source) ? '' : normalizeValue(rule.source);
    if (sourceAddress.startsWith('[group:')) {
      // Extract group type and name from format: [group:address-group:GROUP_NAME]
      const match = sourceAddress.match(/\[group:(address-group|network-group):(.+)\]/);
      if (match) {
        const groupType = match[1];
        const groupName = match[2];
        const groupRadio = form.querySelector('input[name="editSourceAddressType"][value="group"]');
        if (groupRadio) {
          groupRadio.checked = true;
          toggleAddressInput(form, 'source', 'group', 'edit');
          const groupSelect = form.elements.sourceAddressGroup;
          if (groupSelect) {
            groupSelect.value = `${groupType}:${groupName}`;
          }
        }
      }
    } else {
      form.elements.sourceAddress.value = sourceAddress;
    }

    // Handle source port (check for group syntax)
    const sourcePortValue = isAnyValue(rule.source_port) ? '' : normalizeValue(rule.source_port);
    if (sourcePortValue.startsWith('[group:port-group:')) {
      const match = sourcePortValue.match(/\[group:port-group:(.+)\]/);
      if (match) {
        const groupName = match[1];
        const groupRadio = form.querySelector('input[name="editSourcePortType"][value="group"]');
        if (groupRadio) {
          groupRadio.checked = true;
          togglePortInput(form, 'source', 'group', 'edit');
          const groupSelect = form.elements.sourcePortGroup;
          if (groupSelect) {
            groupSelect.value = groupName;
          }
        }
      }
    } else {
      form.elements.sourcePort.value = sourcePortValue;
    }

    // Handle destination address (check for group syntax)
    const destinationAddress = isAnyValue(rule.destination) ? '' : normalizeValue(rule.destination);
    if (destinationAddress.startsWith('[group:')) {
      const match = destinationAddress.match(/\[group:(address-group|network-group):(.+)\]/);
      if (match) {
        const groupType = match[1];
        const groupName = match[2];
        const groupRadio = form.querySelector('input[name="editDestinationAddressType"][value="group"]');
        if (groupRadio) {
          groupRadio.checked = true;
          toggleAddressInput(form, 'destination', 'group', 'edit');
          const groupSelect = form.elements.destinationAddressGroup;
          if (groupSelect) {
            groupSelect.value = `${groupType}:${groupName}`;
          }
        }
      }
    } else {
      form.elements.destinationAddress.value = destinationAddress;
    }

    // Handle destination port (check for group syntax)
    const destinationPortValue = isAnyValue(rule.destination_port) ? '' : normalizeValue(rule.destination_port);
    if (destinationPortValue.startsWith('[group:port-group:')) {
      const match = destinationPortValue.match(/\[group:port-group:(.+)\]/);
      if (match) {
        const groupName = match[1];
        const groupRadio = form.querySelector('input[name="editDestinationPortType"][value="group"]');
        if (groupRadio) {
          groupRadio.checked = true;
          togglePortInput(form, 'destination', 'group', 'edit');
          const groupSelect = form.elements.destinationPortGroup;
          if (groupSelect) {
            groupSelect.value = groupName;
          }
        }
      }
    } else {
      form.elements.destinationPort.value = destinationPortValue;
    }
    // Handle toggle button for disabled state
    const disabledToggle = document.getElementById('editRuleDisabledToggle');
    const disabledHidden = document.getElementById('editRuleDisabled');
    const statusLabel = document.getElementById('editRuleStatusLabel');

    const isDisabled = Boolean(rule.disabled);
    if (disabledToggle && disabledHidden && statusLabel) {
      const isEnabled = !isDisabled;
      disabledToggle.dataset.enabled = isEnabled ? 'true' : 'false';
      disabledHidden.value = isDisabled ? 'true' : 'false';

      if (isEnabled) {
        disabledToggle.classList.remove('bg-gray-500');
        disabledToggle.classList.add('bg-green-500');
        disabledToggle.querySelector('span').classList.remove('translate-x-1');
        disabledToggle.querySelector('span').classList.add('translate-x-8');
        statusLabel.textContent = 'Enabled';
        statusLabel.classList.remove('text-gray-400');
        statusLabel.classList.add('text-green-400');
      } else {
        disabledToggle.classList.remove('bg-green-500');
        disabledToggle.classList.add('bg-gray-500');
        disabledToggle.querySelector('span').classList.remove('translate-x-8');
        disabledToggle.querySelector('span').classList.add('translate-x-1');
        statusLabel.textContent = 'Disabled';
        statusLabel.classList.remove('text-green-400');
        statusLabel.classList.add('text-gray-400');
      }
    }

    applyPresetForRule(form, 'source', sourcePortValue, normalizedProtocol);
    applyPresetForRule(form, 'destination', destinationPortValue, normalizedProtocol);
    if (allowedPortProtocols.includes(normalizedProtocol)) {
      setProtocolValue(form, normalizedProtocol, { force: true });
    }
  }

  firewallNs.forms = {
    resetAddForm,
    serializeForm,
    normalizePayload,
    populateEditForm,
    applyPresetForRule,
    setupPortPresets,
    setProtocolValue,
    setupGroupToggles,
    resetGroupToggles,
  };
})(window);

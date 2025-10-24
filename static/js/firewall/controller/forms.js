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
    const portsProvided = Boolean(normalized.sourcePort) || Boolean(normalized.destinationPort);
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
    form.elements.sourceAddress.value = isAnyValue(rule.source) ? '' : normalizeValue(rule.source);
    const sourcePortValue = isAnyValue(rule.source_port) ? '' : normalizeValue(rule.source_port);
    form.elements.sourcePort.value = sourcePortValue;
    form.elements.destinationAddress.value = isAnyValue(rule.destination) ? '' : normalizeValue(rule.destination);
    const destinationPortValue = isAnyValue(rule.destination_port) ? '' : normalizeValue(rule.destination_port);
    form.elements.destinationPort.value = destinationPortValue;
    form.elements.disabled.checked = Boolean(rule.disabled);

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
  };
})(window);

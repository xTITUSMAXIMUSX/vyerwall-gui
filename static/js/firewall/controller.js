 (function initFirewallController(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const constants = firewallNs.constants;
  const utils = firewallNs.utils;
  const fwState = firewallNs.state;
  const state = fwState.data;

  const selectors = constants.selectors;
  const allowedPortProtocols = constants.allowedPortProtocols;
  const defaultPortProtocol = constants.defaultPortProtocol;
  const actionMetaMap = constants.labels.actions;

  const {
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
  } = utils;

  let modals = {};
  let forms = {};
  let formButtons = {};
  let confirmButtons = {};
  let confirmSpinners = {};
  let infoLabels = {};
  let reorderControls = {};
  let reorderSpinner = null;
  let reorderSaveLabel = null;
  let dragState = { index: null };

  function getActionMeta(action) {
    const key = normalizeValue(action).toLowerCase();
    return actionMetaMap[key] || actionMetaMap.fallback;
  }

  function clearDropTargets() {
    document
      .querySelectorAll(`${selectors.tableBody} tr.firewall-drop-target`)
      .forEach((row) => row.classList.remove('firewall-drop-target'));
  }

  function markDropTarget(row) {
    if (!row) return;
    if (!row.classList.contains('firewall-drop-target')) {
      clearDropTargets();
      row.classList.add('firewall-drop-target');
    }
  }

  function updateAddButtonState() {
    const addButton = document.querySelector(selectors.addRuleButton);
    if (!addButton) {
      return;
    }
    const disabled = state.orderDirty || !state.selectedName;
    addButton.disabled = disabled;
    addButton.classList.toggle('opacity-60', disabled);
    addButton.classList.toggle('cursor-not-allowed', disabled);
  }

  function highlightZone(zone) {
    document.querySelectorAll('.firewall-zone-item').forEach((btn) => {
      if (btn.dataset.zone === zone) {
        btn.classList.add('bg-gray-700');
      } else {
        btn.classList.remove('bg-gray-700');
      }
    });
  }

  function renderZoneList() {
    const listEl = document.querySelector(selectors.zoneList);
    const emptyEl = document.getElementById('firewallZoneEmpty');
    if (!listEl) {
      return;
    }

    const zones = Array.isArray(state.zoneList) ? state.zoneList : [];
    if (!zones.length) {
      listEl.innerHTML = '';
      listEl.classList.add('hidden');
      if (emptyEl) {
        emptyEl.classList.remove('hidden');
      }
      return;
    }

    const items = zones
      .map((zone) => {
        const safeZone = escapeHtml(zone);
        const isSelected = state.selectedZone === zone;
        const baseClasses = 'w-full text-left px-4 py-3 flex items-center gap-2 firewall-zone-item hover:bg-gray-700 transition-colors';
        const stateClasses = isSelected ? ' bg-gray-700' : '';
        return `
          <li>
            <button class="${baseClasses}${stateClasses}" data-zone="${safeZone}">
              <span class="material-icons text-blue-400 text-sm">layers</span>
              <span class="truncate">${safeZone}</span>
            </button>
          </li>
        `;
      })
      .join('');

    listEl.innerHTML = items;
    listEl.classList.remove('hidden');
    if (emptyEl) {
      emptyEl.classList.add('hidden');
    }
    bindZoneButtons();
    renderCreateZoneInterfaceOptions();
  }

  function renderCreateZoneInterfaceOptions() {
    const select = document.getElementById('createZoneInterface');
    const hint = document.getElementById('createZoneInterfaceHint');
    if (!select) {
      return;
    }

    const interfaces = Array.isArray(state.interfaces.unassigned) ? state.interfaces.unassigned : [];
    const previousValue = select.value;

    const options = [
      '<option value="">Select interface...</option>',
      ...interfaces.map((iface) => `<option value="${escapeHtml(iface)}">${escapeHtml(iface)}</option>`),
    ];
    select.innerHTML = options.join('');

    if (interfaces.length === 0) {
      select.disabled = true;
      if (formButtons.createZoneSubmit) {
        formButtons.createZoneSubmit.disabled = true;
        formButtons.createZoneSubmit.classList.add('opacity-60', 'cursor-not-allowed');
      }
      if (hint) {
        hint.textContent =
          'No unassigned interfaces are available. Add or free an interface before creating a new zone.';
      }
    } else {
      select.disabled = false;
      if (formButtons.createZoneSubmit) {
        formButtons.createZoneSubmit.disabled = false;
        formButtons.createZoneSubmit.classList.remove('opacity-60', 'cursor-not-allowed');
      }
      if (hint) {
        hint.textContent =
          'Select an unassigned interface to attach to the new zone.';
      }
      if (previousValue && interfaces.includes(previousValue)) {
        select.value = previousValue;
      }
    }
  }

  function renderPairList(zone) {
    const pairList = document.querySelector(selectors.pairList);
    if (!pairList) {
      return;
    }

    const pairs = (zone && state.zoneGroups[zone]) ? state.zoneGroups[zone] : [];
    if (!pairs.length) {
      const message = zone
        ? `No firewall rule sets for ${escapeHtml(zone)}.`
        : 'Select a zone on the left to view firewall rule sets.';
      pairList.innerHTML = `<li class="p-4 text-sm text-gray-400">${message}</li>`;
      bindPairButtons();
      updateAddButtonState();
      return;
    }

    const items = pairs
      .map((pair) => {
        const meta = state.metadata[pair.name] || {};
        const isSelected = state.selectedName === pair.name;
        const zoneLabel = meta.zone_label
          ? escapeHtml(meta.zone_label)
          : escapeHtml(pair.destination ? `${zone} -> ${pair.destination}` : zone);
        const description = meta.description ? `<span class="text-xs text-gray-400">${escapeHtml(meta.description)}</span>` : '';

        const baseClasses = 'w-full text-left px-4 py-3 flex items-center justify-between rounded firewall-pair-item transition-colors';
        const stateClasses = isSelected ? ' bg-gray-700' : ' hover:bg-gray-700';

        return `
          <li>
            <button class="${baseClasses}${stateClasses}" data-firewall-name="${escapeHtml(pair.name)}" data-zone="${escapeHtml(zone)}">
              <div class="flex flex-col leading-tight">
                <span class="font-semibold text-white">${escapeHtml(pair.name)}</span>
                <span class="text-xs text-indigo-300 uppercase tracking-wide">${zoneLabel}</span>
                ${description}
              </div>
              <span class="material-icons text-sm text-gray-400">chevron_right</span>
            </button>
          </li>
        `;
      })
      .join('');

    pairList.innerHTML = items;
    bindPairButtons();
    updateAddButtonState();
  }

  function selectZone(zone) {
    const zoneKey = (zone || '').toUpperCase();
    if (!zoneKey) {
      return;
    }

    const pairs = state.zoneGroups[zoneKey] || [];
    state.selectedZone = zoneKey;

    let targetName = state.selectedName;
    if (!pairs.some((pair) => pair.name === targetName)) {
      targetName = pairs.length ? pairs[0].name : null;
    }
    state.selectedName = targetName;

    highlightZone(zoneKey);
    renderPairList(zoneKey);

    if (targetName) {
      fetchFirewallDetails(targetName);
    } else {
      state.rules = [];
      state.rulesBaseline = [];
      renderMetadata(null, {});
      renderRules();
      setOrderDirty(false);
    }
  }

  function bindZoneButtons() {
    document.querySelectorAll('.firewall-zone-item').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before changing zones.');
          return;
        }
        selectZone(btn.dataset.zone);
      });
    });
  }

  function bindPairButtons() {
    document.querySelectorAll('.firewall-pair-item').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before switching firewall rule sets.');
          return;
        }
        const zone = (btn.dataset.zone || '').toUpperCase();
        const name = btn.dataset.firewallName;
        if (!name) {
          return;
        }
        state.selectedZone = zone || state.selectedZone;
        state.selectedName = name;
        highlightZone(state.selectedZone);
        renderPairList(state.selectedZone);
        fetchFirewallDetails(name);
      });
    });
  }

  function getPortControls(form, kind) {
    if (!form) {
      return { select: null, input: null };
    }
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

  function computeNextRuleNumber() {
    if (!state.rules || state.rules.length === 0) {
      return 100;
    }
    const numbers = state.rules
      .map((rule) => parseInt(rule.number, 10))
      .filter((value) => Number.isInteger(value));
    if (numbers.length === 0) {
      return 100;
    }
    return Math.max(...numbers) + 1;
  }

  function resetAddForm() {
    if (!forms.add) return;
    forms.add.reset();
    const nextNumber = computeNextRuleNumber();
    if (forms.add.elements.number) {
      forms.add.elements.number.value = nextNumber;
    }
    if (forms.add.elements.protocol) {
      forms.add.elements.protocol.value = defaultPortProtocol;
    }
    applyPortPreset(forms.add, 'source', {
      selectValue: 'other',
      existingValue: '',
      protocolOverride: defaultPortProtocol,
      preserveInput: false,
    });
    applyPortPreset(forms.add, 'destination', {
      selectValue: 'other',
      existingValue: '',
      protocolOverride: defaultPortProtocol,
      preserveInput: false,
    });
  }

  function resetCreateZoneForm() {
    if (!forms.createZone) return;
    forms.createZone.reset();
    const interfaceSelect = forms.createZone.querySelector('[name="interface"]');
    if (interfaceSelect) {
      interfaceSelect.value = '';
    }
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

  function setOrderDirty(flag) {
    state.orderDirty = flag;
    if (reorderControls.container) {
      reorderControls.container.classList.toggle('hidden', !flag);
    }
    if (reorderControls.save) {
      reorderControls.save.disabled = !flag;
    }
    if (reorderControls.cancel) {
      reorderControls.cancel.disabled = !flag;
    }
    updateAddButtonState();
  }

  function mapRule(rule) {
    return {
      ...rule,
      id: String(rule.number),
      number: String(rule.number),
    };
  }

  function applyFirewallPayload(name, payload) {
    if (!payload) {
      state.rules = [];
      state.rulesBaseline = [];
      renderMetadata(name, {});
      renderRules();
      setOrderDirty(false);
      renderPairList(state.selectedZone);
      updateAddButtonState();
      return;
    }

    state.selectedName = name;
    state.metadata[name] = payload.metadata || {};
    state.rules = (payload.rules || []).map(mapRule);
    state.rulesBaseline = cloneRules(state.rules);

    const meta = state.metadata[name] || {};
    const zoneFromMeta = (meta.source_zone || '').toUpperCase();
    const destinationZone = (meta.destination_zone || '').toUpperCase();

    if (zoneFromMeta) {
      Object.keys(state.zoneGroups).forEach((zoneKey) => {
        const list = state.zoneGroups[zoneKey];
        if (!Array.isArray(list)) {
          return;
        }
        state.zoneGroups[zoneKey] = list.filter((pair) => pair.name !== name);
      });

      if (!Array.isArray(state.zoneGroups[zoneFromMeta])) {
        state.zoneGroups[zoneFromMeta] = [];
      }

      const existingPair = state.zoneGroups[zoneFromMeta].find((pair) => pair.name === name);
      if (existingPair) {
        existingPair.destination = destinationZone;
      } else {
        state.zoneGroups[zoneFromMeta].push({ name, destination: destinationZone });
        state.zoneGroups[zoneFromMeta].sort((a, b) => {
          const destA = (a.destination || '').toString();
          const destB = (b.destination || '').toString();
          const destCompare = destA.localeCompare(destB);
          if (destCompare !== 0) {
            return destCompare;
          }
          return a.name.localeCompare(b.name);
        });
      }
    }

    let zoneListUpdated = false;
    if (zoneFromMeta) {
      if (!Array.isArray(state.zoneList)) {
        state.zoneList = [];
      }
      if (!state.zoneList.includes(zoneFromMeta)) {
        state.zoneList.push(zoneFromMeta);
        state.zoneList.sort((a, b) => a.localeCompare(b));
        zoneListUpdated = true;
      }
    }

    if (zoneFromMeta && zoneFromMeta !== state.selectedZone) {
      state.selectedZone = zoneFromMeta;
    }

    if (zoneListUpdated) {
      renderZoneList();
    }
    highlightZone(state.selectedZone);

    renderMetadata(name, payload.metadata || {});
    renderRules();
    setOrderDirty(false);
    renderPairList(state.selectedZone);
    updateAddButtonState();
    resetAddForm();
  }

  function applyZoneUpdate(payload) {
    if (!payload || typeof payload !== 'object') {
      return;
    }

    if (payload.interfaces && typeof payload.interfaces === 'object') {
      const unassigned = Array.isArray(payload.interfaces.unassigned)
        ? payload.interfaces.unassigned.slice().sort((a, b) => a.localeCompare(b))
        : [];
      state.interfaces = { ...state.interfaces, unassigned };
    }

    if (Array.isArray(payload.zones)) {
      state.zoneList = payload.zones
        .map((zone) => (zone || '').toUpperCase())
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));
    }

    if (payload.zoneGroups && typeof payload.zoneGroups === 'object') {
      const normalizedGroups = {};
      Object.entries(payload.zoneGroups).forEach(([zone, entries]) => {
        const zoneKey = (zone || '').toUpperCase();
        if (!zoneKey) {
          return;
        }
        const mappedEntries = Array.isArray(entries)
          ? entries.map((entry) => ({
              name: entry.name,
              destination: (entry.destination || '').toUpperCase(),
            }))
          : [];
        mappedEntries.sort((a, b) => {
          const destA = (a.destination || '').toString();
          const destB = (b.destination || '').toString();
          const destCompare = destA.localeCompare(destB);
          if (destCompare !== 0) {
            return destCompare;
          }
          return (a.name || '').localeCompare(b.name || '');
        });
        normalizedGroups[zoneKey] = mappedEntries;
      });
      state.zoneGroups = normalizedGroups;
    }

    if (!Array.isArray(state.zoneList) || state.zoneList.length === 0) {
      state.zoneList = Object.keys(state.zoneGroups || {}).sort((a, b) => a.localeCompare(b));
    }

    if (payload.metadata && typeof payload.metadata === 'object') {
      state.metadata = payload.metadata;
    }

    if (Array.isArray(payload.names)) {
      state.names = payload.names;
    }

    let targetZone = payload.selectedZone || state.selectedZone || (state.zoneList[0] || null);
    targetZone = targetZone ? String(targetZone).toUpperCase() : null;
    state.selectedZone = targetZone;

    const pairs = targetZone && state.zoneGroups[targetZone] ? state.zoneGroups[targetZone] : [];
    let targetFirewall = payload.selectedFirewall || state.selectedName || (pairs[0] && pairs[0].name) || null;
    targetFirewall = targetFirewall || null;
    state.selectedName = targetFirewall;

    setOrderDirty(false);

    renderZoneList();
    highlightZone(state.selectedZone);
    renderPairList(state.selectedZone);
    renderCreateZoneInterfaceOptions();

    if (state.selectedName) {
      const existingMeta = state.metadata[state.selectedName] || {};
      renderMetadata(state.selectedName, existingMeta);
      state.rules = [];
      state.rulesBaseline = [];
      renderRules();
      updateAddButtonState();
      fetchFirewallDetails(state.selectedName);
    } else {
      state.rules = [];
      state.rulesBaseline = [];
      renderMetadata(null, {});
      renderRules();
      updateAddButtonState();
    }
  }

  function renderMetadata(name, metadata = {}) {
    const titleEl = document.querySelector(selectors.title);
    const descriptionEl = document.querySelector(selectors.description);
    const defaultActionEl = document.querySelector(selectors.defaultAction);
    const zonePairEl = document.querySelector(selectors.zonePair);
    const ruleCountEl = document.querySelector(selectors.ruleCount);

    if (titleEl) {
      titleEl.textContent = name || 'No Firewall Selected';
    }

    if (descriptionEl) {
      if (metadata.description) {
        descriptionEl.textContent = metadata.description;
        descriptionEl.classList.remove('text-gray-500');
      } else {
        descriptionEl.textContent = 'None';
        descriptionEl.classList.add('text-gray-500');
      }
    }

    if (zonePairEl) {
      if (metadata.zone_label) {
        zonePairEl.textContent = metadata.zone_label;
        zonePairEl.classList.remove('text-gray-500');
      } else {
        zonePairEl.textContent = 'Unassigned';
        zonePairEl.classList.add('text-gray-500');
      }
    }

    if (defaultActionEl) {
      defaultActionEl.textContent = metadata.default_action || 'accept';
    }

    if (ruleCountEl) {
      ruleCountEl.textContent = (state.rules || []).length;
    }
  }

  function renderEmptyRules(tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="px-4 py-6 text-center text-gray-400">
          No rules defined for this firewall.
        </td>
      </tr>
    `;
  }

  function renderRules() {
    const tbody = document.querySelector(selectors.tableBody);
    if (!tbody) {
      return;
    }

    clearDropTargets();

    const rules = state.rules || [];
    if (!rules.length) {
      renderEmptyRules(tbody);
      bindRuleActionButtons();
      return;
    }

    const canDrag = rules.length > 1;
    const rows = rules.map((rule, index) => {
      const rowClasses = ['border-t', 'border-gray-800', 'transition-colors'];
      if (canDrag) {
        rowClasses.push('cursor-grab', 'draggable-row');
      }
      if (rule.disabled) {
        rowClasses.push('bg-yellow-500/10', 'disabled-firewall-rule');
      }
      const toggleClasses = rule.disabled
        ? 'text-green-400 hover:text-green-300'
        : 'text-yellow-400 hover:text-yellow-300';
      const toggleIcon = rule.disabled ? 'check_circle' : 'block';
      const protocolDisplay = escapeHtml(formatProtocolDisplay(rule.protocol));
      const sourceDisplay = escapeHtml(formatEndpointDisplay(rule.source));
      const sourcePortDisplay = escapeHtml(formatPortDisplay(rule.source_port));
      const destinationDisplay = escapeHtml(formatEndpointDisplay(rule.destination));
      const destinationPortDisplay = escapeHtml(formatPortDisplay(rule.destination_port));
      const descriptionDisplay = escapeHtml(rule.description || '-');
      const actionMeta = getActionMeta(rule.action);
      const actionLabelEscaped = escapeHtml(actionMeta.label);
      return `
      <tr class="${rowClasses.join(' ')}" draggable="${canDrag}" data-rule-id="${rule.id}" data-index="${index}" data-disabled="${rule.disabled ? 'true' : 'false'}">
        <td class="px-4 py-3 font-mono text-gray-100">
          <div class="flex items-center gap-2">
            <span class="material-icons text-gray-500 text-base drag-handle">drag_indicator</span>
            <span class="material-icons text-base ${actionMeta.className}" title="${actionLabelEscaped}">${actionMeta.icon}</span>
            <span class="sr-only">${actionLabelEscaped}</span>
            ${rule.number}
          </div>
        </td>
        <td class="px-4 py-3">${protocolDisplay}</td>
        <td class="px-4 py-3">${sourceDisplay}</td>
        <td class="px-4 py-3">${sourcePortDisplay}</td>
        <td class="px-4 py-3">${destinationDisplay}</td>
        <td class="px-4 py-3">${destinationPortDisplay}</td>
        <td class="px-4 py-3">${descriptionDisplay}</td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-2 text-sm">
            <button class="text-blue-400 hover:text-blue-300 btn-rule-edit flex items-center gap-1" data-rule-number="${rule.id}">
              <span class="material-icons text-base">edit</span>
              <span class="sr-only">Edit</span>
            </button>
            <button class="text-red-400 hover:text-red-300 btn-rule-delete flex items-center gap-1" data-rule-number="${rule.id}">
              <span class="material-icons text-base">delete</span>
              <span class="sr-only">Delete</span>
            </button>
            <button class="${toggleClasses} btn-rule-disable flex items-center gap-1" data-rule-number="${rule.id}">
              <span class="material-icons text-base">${toggleIcon}</span>
              <span class="sr-only">${rule.disabled ? 'Enable' : 'Disable'}</span>
            </button>
          </div>
        </td>
      </tr>
    `;
    });

    tbody.innerHTML = rows.join('');
    bindRuleActionButtons();
    if (canDrag) {
      bindRowDragHandlers();
    }
  }

  function findRule(ruleNumber) {
    return (state.rules || []).find((rule) => String(rule.id) === String(ruleNumber));
  }

  function bindRowDragHandlers() {
    const rows = document.querySelectorAll('#firewallRulesBody tr');
    rows.forEach((row) => {
      row.addEventListener('dragstart', (event) => {
        if (event.target.closest('button')) {
          event.preventDefault();
          return;
        }
        dragState.index = Number(row.dataset.index);
        row.classList.add('opacity-50');
        event.dataTransfer.effectAllowed = 'move';
      });

      row.addEventListener('dragend', () => {
        row.classList.remove('opacity-50');
        clearDropTargets();
        dragState.index = null;
      });

      row.addEventListener('dragover', (event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        markDropTarget(row);
      });

      row.addEventListener('drop', (event) => {
        event.preventDefault();
        if (dragState.index === null) {
          clearDropTargets();
          return;
        }
        const targetIndex = Number(row.dataset.index);
        if (Number.isNaN(targetIndex) || targetIndex === dragState.index) {
          clearDropTargets();
          return;
        }
        const newOrder = cloneRules(state.rules);
        const [moved] = newOrder.splice(dragState.index, 1);
        newOrder.splice(targetIndex, 0, moved);
        updateRulesOrder(newOrder);
        clearDropTargets();
      });

      row.addEventListener('dragleave', (event) => {
        if (!row.contains(event.relatedTarget)) {
          row.classList.remove('firewall-drop-target');
        }
      });
    });
  }

  function updateRulesOrder(newOrder) {
    const baseline = state.rulesBaseline || [];
    const identical =
      newOrder.length === baseline.length &&
      newOrder.every((rule, index) => String(rule.id) === String((baseline[index] || {}).id));

    if (identical) {
      state.rules = cloneRules(baseline);
      setOrderDirty(false);
      renderRules();
      return;
    }

    state.rules = cloneRules(newOrder);
    setOrderDirty(true);
    renderRules();
  }

  function cancelReorder() {
    if (!state.orderDirty) {
      return;
    }
    state.rules = cloneRules(state.rulesBaseline);
    renderRules();
    setOrderDirty(false);
  }

  async function submitReorder() {
    if (!state.orderDirty || !state.selectedName) {
      return;
    }
    const order = state.rules.map((rule) => String(rule.id));
    try {
      toggleButtonLoading(
        reorderControls.save,
        reorderSpinner,
        reorderSaveLabel,
        true,
        'Save Order',
        'Saving...',
      );
      const data = await performRequest(
        `/firewall/rules/api/names/${encodeName(state.selectedName)}/rules/reorder`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order }),
        },
      );
      applyFirewallPayload(state.selectedName, data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to reorder firewall rules.');
    } finally {
      toggleButtonLoading(
        reorderControls.save,
        reorderSpinner,
        reorderSaveLabel,
        false,
        'Save Order',
        'Saving...',
      );
    }
  }

  function bindRuleActionButtons() {
    document.querySelectorAll('.btn-rule-edit').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before editing rules.');
          return;
        }
        openEditModal(btn.dataset.ruleNumber);
      });
    });

    document.querySelectorAll('.btn-rule-delete').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before deleting rules.');
          return;
        }
        openDeleteModal(btn.dataset.ruleNumber);
      });
    });

    document.querySelectorAll('.btn-rule-disable').forEach((btn) => {
      btn.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before toggling rules.');
          return;
        }
        openDisableModal(btn.dataset.ruleNumber);
      });
    });
  }

  function bindListInteractions() {
    bindZoneButtons();
    bindPairButtons();

    const createZoneButton = document.querySelector(selectors.createZoneButton);
    if (createZoneButton) {
      createZoneButton.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before creating new zones.');
          return;
        }
        renderCreateZoneInterfaceOptions();
        resetCreateZoneForm();
        openModal(modals.createZone);
        setTimeout(() => {
          if (!forms.createZone) {
            return;
          }
          const input = forms.createZone.querySelector('[name="zoneName"]');
          if (input) {
            input.focus();
            input.select();
          }
        }, 0);
      });
    }

    const addRuleButton = document.querySelector(selectors.addRuleButton);
    if (addRuleButton) {
      addRuleButton.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before adding rules.');
          return;
        }
        if (!state.selectedName) {
          alert('Select a zone and rule set before adding rules.');
          return;
        }
        resetAddForm();
        openModal(modals.add);
      });
    }

    updateAddButtonState();
  }

  async function fetchFirewallDetails(name) {
    try {
      state.isLoading = true;
      const response = await fetch(`/firewall/rules/api/names/${encodeName(name)}`);
      if (!response.ok) {
        throw new Error(`Unable to load firewall ${name}`);
      }
      const payload = await response.json();
      if (payload.status !== 'ok') {
        throw new Error(payload.message || 'Unknown error');
      }
      applyFirewallPayload(name, payload.data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to load firewall rules.');
    } finally {
      state.isLoading = false;
    }
  }

  async function performRequest(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.status !== 'ok') {
      const message = payload.message || `Request failed with status ${response.status}`;
      throw new Error(message);
    }
    return payload.data;
  }

  function openModal(modal) {
    if (!modal) return;
    modal.classList.remove('hidden');
  }

  function closeModal(modalId) {
    const modal = typeof modalId === 'string' ? document.getElementById(modalId) : modalId;
    if (!modal) return;
    modal.classList.add('hidden');
  }

  function populateEditForm(rule) {
    if (!forms.edit || !rule) return;
    forms.edit.elements.originalNumber.value = rule.number;
    forms.edit.elements.number.value = rule.number;
    forms.edit.elements.action.value = rule.action || 'accept';

    let normalizedProtocol = normalizeValue(rule.protocol).toLowerCase();
    if (isAllProtocol(rule.protocol)) {
      normalizedProtocol = 'all';
    }
    const protocolSelect = forms.edit.elements.protocol;
    if (protocolSelect) {
      const availableValues = Array.from(protocolSelect.options).map((opt) => opt.value);
      protocolSelect.value = availableValues.includes(normalizedProtocol) ? normalizedProtocol : '';
    }

    forms.edit.elements.description.value = rule.description || '';
    forms.edit.elements.sourceAddress.value = isAnyValue(rule.source) ? '' : normalizeValue(rule.source);
    const sourcePortValue = isAnyValue(rule.source_port) ? '' : normalizeValue(rule.source_port);
    forms.edit.elements.sourcePort.value = sourcePortValue;
    forms.edit.elements.destinationAddress.value = isAnyValue(rule.destination) ? '' : normalizeValue(rule.destination);
    const destinationPortValue = isAnyValue(rule.destination_port) ? '' : normalizeValue(rule.destination_port);
    forms.edit.elements.destinationPort.value = destinationPortValue;
    forms.edit.elements.disabled.checked = Boolean(rule.disabled);

    applyPresetForRule(forms.edit, 'source', sourcePortValue, normalizedProtocol);
    applyPresetForRule(forms.edit, 'destination', destinationPortValue, normalizedProtocol);
    if (allowedPortProtocols.includes(normalizedProtocol)) {
      setProtocolValue(forms.edit, normalizedProtocol, { force: true });
    }
  }

  function openEditModal(ruleNumber) {
    const rule = findRule(ruleNumber);
    if (!rule) {
      alert('Rule not found.');
      return;
    }
    populateEditForm(rule);
    openModal(modals.edit);
  }

  function openDeleteModal(ruleNumber) {
    const rule = findRule(ruleNumber);
    if (!rule) {
      alert('Rule not found.');
      return;
    }
    if (infoLabels.delete) {
      const target = infoLabels.delete.querySelector('span.font-semibold');
      if (target) {
        target.textContent = rule.number;
      }
    }
    if (confirmButtons.delete) {
      confirmButtons.delete.dataset.ruleNumber = rule.number;
    }
    openModal(modals.delete);
  }

  function openDisableModal(ruleNumber) {
    const rule = findRule(ruleNumber);
    if (!rule) {
      alert('Rule not found.');
      return;
    }
    const actionLabel = rule.disabled ? 'enable' : 'disable';
    if (infoLabels.disable) {
      infoLabels.disable.innerHTML = `Are you sure you want to ${actionLabel} rule <span class="font-semibold">${rule.number}</span>?`;
    }
    if (confirmButtons.disable) {
      confirmButtons.disable.dataset.ruleNumber = rule.number;
      confirmButtons.disable.dataset.toggleAction = actionLabel;
    }
    openModal(modals.disable);
  }

  function bindModalCloseHandlers() {
    document.querySelectorAll('[data-close-modal]').forEach((btn) => {
      btn.addEventListener('click', () => closeModal(btn.dataset.closeModal));
    });
    Object.values(modals).forEach((modal) => {
      if (!modal) return;
      modal.addEventListener('click', (event) => {
        if (event.target === modal) {
          closeModal(modal);
        }
      });
    });
  }

  function bindFormHandlers() {
    if (forms.createZone) {
      forms.createZone.addEventListener('submit', (event) => {
        event.preventDefault();
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before creating new zones.');
          return;
        }
        submitCreateZone();
      });
    }

    if (forms.add) {
      forms.add.addEventListener('submit', (event) => {
        event.preventDefault();
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before adding rules.');
          return;
        }
        submitAddRule();
      });
    }

    if (forms.edit) {
      forms.edit.addEventListener('submit', (event) => {
        event.preventDefault();
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before editing rules.');
          return;
        }
        submitEditRule();
      });
    }

    if (confirmButtons.delete) {
      confirmButtons.delete.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before deleting rules.');
          return;
        }
        submitDeleteRule(confirmButtons.delete.dataset.ruleNumber);
      });
    }

    if (confirmButtons.disable) {
      confirmButtons.disable.addEventListener('click', () => {
        if (state.orderDirty) {
          alert('Save or cancel the current reorder before toggling rules.');
          return;
        }
        submitToggleRule(
          confirmButtons.disable.dataset.ruleNumber,
          confirmButtons.disable.dataset.toggleAction,
        );
      });
    }
  }

  function bindReorderButtons() {
    if (reorderControls.save) {
      reorderControls.save.addEventListener('click', submitReorder);
    }
    if (reorderControls.cancel) {
      reorderControls.cancel.addEventListener('click', cancelReorder);
    }
  }

  async function submitCreateZone() {
    if (!forms.createZone) {
      return;
    }
    const formData = new FormData(forms.createZone);
    const zoneName = String(formData.get('zoneName') || '').trim();
    const interfaceName = String(formData.get('interface') || '').trim();
    if (!zoneName) {
      alert('Zone name is required.');
      return;
    }
    if (!interfaceName) {
      alert('Select an interface to attach to the new zone.');
      return;
    }

    try {
      toggleButtonLoading(
        formButtons.createZoneSubmit,
        formButtons.createZoneSpinner,
        formButtons.createZoneLabel,
        true,
        'Create Zone',
        'Creating...',
      );
      const data = await performRequest('/firewall/rules/api/zones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zoneName, interface: interfaceName }),
      });
      closeModal(modals.createZone);
      resetCreateZoneForm();
      applyZoneUpdate(data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to create firewall zone.');
    } finally {
      toggleButtonLoading(
        formButtons.createZoneSubmit,
        formButtons.createZoneSpinner,
        formButtons.createZoneLabel,
        false,
        'Create Zone',
        'Creating...',
      );
    }
  }

  async function submitAddRule() {
    const firewallName = state.selectedName;
    if (!firewallName) {
      alert('Select a firewall before adding rules.');
      return;
    }
    const rawPayload = serializeForm(forms.add);
    const payload = normalizePayload(rawPayload, forms.add);

    try {
      toggleButtonLoading(
        formButtons.addSubmit,
        formButtons.addSpinner,
        formButtons.addLabel,
        true,
        'Create Rule',
        'Creating...',
      );
      const data = await performRequest(
        `/firewall/rules/api/names/${encodeName(firewallName)}/rules`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      );
      closeModal(modals.add);
      applyFirewallPayload(firewallName, data);
      resetAddForm();
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to add firewall rule.');
    } finally {
      toggleButtonLoading(
        formButtons.addSubmit,
        formButtons.addSpinner,
        formButtons.addLabel,
        false,
        'Create Rule',
        'Creating...',
      );
    }
  }

  async function submitEditRule() {
    const firewallName = state.selectedName;
    if (!firewallName) {
      alert('Select a firewall before editing rules.');
      return;
    }
    const rawPayload = serializeForm(forms.edit);
    const payload = normalizePayload(rawPayload, forms.edit);
    const originalNumber = rawPayload.originalNumber;

    try {
      toggleButtonLoading(
        formButtons.editSubmit,
        formButtons.editSpinner,
        formButtons.editLabel,
        true,
        'Save Changes',
        'Saving...',
      );
      const data = await performRequest(
        `/firewall/rules/api/names/${encodeName(firewallName)}/rules/${encodeURIComponent(originalNumber)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      );
      closeModal(modals.edit);
      applyFirewallPayload(firewallName, data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to update firewall rule.');
    } finally {
      toggleButtonLoading(
        formButtons.editSubmit,
        formButtons.editSpinner,
        formButtons.editLabel,
        false,
        'Save Changes',
        'Saving...',
      );
    }
  }

  async function submitDeleteRule(ruleNumber) {
    const firewallName = state.selectedName;
    if (!firewallName || !ruleNumber) {
      alert('Select a firewall before deleting rules.');
      return;
    }

    try {
      toggleButtonLoading(
        confirmButtons.delete,
        confirmSpinners.deleteSpinner,
        confirmSpinners.deleteLabel,
        true,
        'Delete',
        'Deleting...',
      );
      const data = await performRequest(
        `/firewall/rules/api/names/${encodeName(firewallName)}/rules/${encodeURIComponent(ruleNumber)}`,
        { method: 'DELETE' },
      );
      closeModal(modals.delete);
      applyFirewallPayload(firewallName, data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to delete firewall rule.');
    } finally {
      toggleButtonLoading(
        confirmButtons.delete,
        confirmSpinners.deleteSpinner,
        confirmSpinners.deleteLabel,
        false,
        'Delete',
        'Deleting...',
      );
    }
  }

  async function submitToggleRule(ruleNumber, toggleAction) {
    const firewallName = state.selectedName;
    if (!firewallName || !ruleNumber) {
      alert('Select a firewall before toggling rules.');
      return;
    }

    const disableFlag = toggleAction === 'disable';
    try {
      toggleButtonLoading(
        confirmButtons.disable,
        confirmSpinners.disableSpinner,
        confirmSpinners.disableLabel,
        true,
        'Confirm',
        disableFlag ? 'Disabling...' : 'Enabling...',
      );
      const data = await performRequest(
        `/firewall/rules/api/names/${encodeName(firewallName)}/rules/${encodeURIComponent(ruleNumber)}/toggle`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ disabled: disableFlag }),
        },
      );
      closeModal(modals.disable);
      applyFirewallPayload(firewallName, data);
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to toggle firewall rule state.');
    } finally {
      toggleButtonLoading(
        confirmButtons.disable,
        confirmSpinners.disableSpinner,
        confirmSpinners.disableLabel,
        false,
        'Confirm',
        disableFlag ? 'Disabling...' : 'Enabling...',
      );
    }
  }

  function initializeFromServer() {
    const bootstrap = window.FIREWALL_RULES_VIEW_DATA;
    if (!bootstrap) {
      renderMetadata(null, {});
      renderRules();
      setOrderDirty(false);
      highlightZone(null);
      renderPairList(null);
      updateAddButtonState();
      renderCreateZoneInterfaceOptions();
      return;
    }

    const {
      names,
      metadata,
      zoneGroups,
      initialZone,
      initialName,
      initialDetails,
      firewall_zone_list: zoneListRaw,
      initialInterfaces,
    } = bootstrap;

    state.names = names || [];
    state.metadata = metadata || {};
    state.zoneGroups = {};

    if (initialInterfaces && typeof initialInterfaces === 'object') {
      const unassigned = Array.isArray(initialInterfaces.unassigned)
        ? initialInterfaces.unassigned.slice().sort((a, b) => a.localeCompare(b))
        : [];
      state.interfaces = { ...state.interfaces, unassigned };
    }

    if (zoneGroups) {
      Object.entries(zoneGroups).forEach(([zone, pairs]) => {
        const zoneKey = (zone || '').toUpperCase();
        if (!zoneKey) {
          return;
        }
        const normalizedPairs = (pairs || []).map((pair) => ({
          name: pair.name,
          destination: (pair.destination || '').toUpperCase(),
        }));
        normalizedPairs.sort((a, b) => {
          const destA = (a.destination || '').toString();
          const destB = (b.destination || '').toString();
          const destCompare = destA.localeCompare(destB);
          if (destCompare !== 0) {
            return destCompare;
          }
          return (a.name || '').localeCompare(b.name || '');
        });
        state.zoneGroups[zoneKey] = normalizedPairs;
      });
    }

    const sanitizedZoneList = Array.isArray(zoneListRaw)
      ? zoneListRaw.map((zone) => (zone || '').toUpperCase()).filter(Boolean)
      : [];
    const zoneKeys = Object.keys(state.zoneGroups || {});
    const combinedZones = new Set([...sanitizedZoneList, ...zoneKeys]);
    state.zoneList = Array.from(combinedZones).sort((a, b) => a.localeCompare(b));

    const initialZoneKey = (initialZone || state.zoneList[0] || '').toUpperCase();
    state.selectedZone = initialZoneKey || null;
    state.selectedName = initialName || null;

    if (!state.selectedName && state.selectedZone) {
      const zonePairs = state.zoneGroups[state.selectedZone] || [];
      if (zonePairs.length) {
        state.selectedName = zonePairs[0].name;
      }
    }

    renderZoneList();
    highlightZone(state.selectedZone);
    renderPairList(state.selectedZone);

    if (state.selectedName && initialDetails) {
      applyFirewallPayload(state.selectedName, initialDetails);
    } else {
      const fallbackMetadata = (state.selectedName && state.metadata[state.selectedName]) || {};
      renderMetadata(state.selectedName, fallbackMetadata);
      renderRules();
      setOrderDirty(false);
      updateAddButtonState();
    }
  }

  function bindPortPresets() {
    setupPortPresets(forms.add, 'other');
    setupPortPresets(forms.edit);
  }

  function init() {
    fwState.initializeDomReferences();
    modals = fwState.modals;
    forms = fwState.forms;
    formButtons = fwState.formButtons;
    confirmButtons = fwState.confirmButtons;
    confirmSpinners = fwState.confirmSpinners;
    infoLabels = fwState.infoLabels;
    reorderControls = fwState.reorderControls;
    reorderSpinner = fwState.reorderSpinner;
    reorderSaveLabel = fwState.reorderSaveLabel;
    dragState = fwState.dragState;

    bindModalCloseHandlers();
    bindFormHandlers();
    bindReorderButtons();
    bindPortPresets();
    bindListInteractions();
    initializeFromServer();
    resetAddForm();
  }

  firewallNs.controller = { init };
})(window);

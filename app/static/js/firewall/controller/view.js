(function initFirewallView(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const constants = firewallNs.constants || {};
  const utils = firewallNs.utils || {};
  const fwState = firewallNs.state;
  const state = fwState ? fwState.data : {};

  const selectors = constants.selectors || {};
  const actionMetaMap = (constants.labels && constants.labels.actions) || {};

  const {
    escapeHtml = (value) => String(value ?? ''),
    formatProtocolDisplay = (value) => value,
    formatEndpointDisplay = (value) => value,
    formatPortDisplay = (value) => value,
    formatGroupDisplay = (value) => value,
    cloneRules = (rules) => (rules || []).map((rule) => ({ ...rule })),
  } = utils;

  function getActionMeta(action) {
    const key = String(action || '').trim().toLowerCase();
    return actionMetaMap[key] || actionMetaMap.fallback || { icon: 'radio_button_unchecked', className: 'text-gray-500', label: 'No action set' };
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

  function renderZoneList(onSelect) {
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

    if (typeof onSelect === 'function') {
      listEl.querySelectorAll('.firewall-zone-item').forEach((btn) => {
        btn.addEventListener('click', () => onSelect(btn.dataset.zone));
      });
    }
  }

  function renderPairList(zone, onSelect) {
    const pairList = document.querySelector(selectors.pairList);
    if (!pairList) {
      return;
    }

    const zoneKey = (zone || '').toUpperCase();
    const pairs = zoneKey && state.zoneGroups ? state.zoneGroups[zoneKey] : [];
    if (!pairs || !pairs.length) {
      const message = zoneKey
        ? `No firewall rule sets for ${escapeHtml(zoneKey)}.`
        : 'Select a zone on the left to view firewall rule sets.';
      pairList.innerHTML = `<li class="p-4 text-sm text-gray-400">${message}</li>`;
      return;
    }

    const items = pairs
      .map((pair) => {
        const meta = (state.metadata && state.metadata[pair.name]) || {};
        const isSelected = state.selectedName === pair.name;
        const zoneLabel = meta.zone_label
          ? escapeHtml(meta.zone_label)
          : escapeHtml(pair.destination ? `${zoneKey} -> ${pair.destination}` : zoneKey);
        const description = meta.description ? `<span class="text-xs text-gray-400">${escapeHtml(meta.description)}</span>` : '';

        const baseClasses = 'w-full text-left px-4 py-3 flex items-center justify-between rounded firewall-pair-item transition-colors';
        const stateClasses = isSelected ? ' bg-gray-700' : ' hover:bg-gray-700';

        return `
          <li>
            <button class="${baseClasses}${stateClasses}"
                    data-firewall-name="${escapeHtml(pair.name)}"
                    data-zone="${escapeHtml(zoneKey)}">
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

    if (typeof onSelect === 'function') {
      pairList.querySelectorAll('.firewall-pair-item').forEach((btn) => {
        btn.addEventListener('click', () => {
          onSelect(btn.dataset.firewallName, btn.dataset.zone);
        });
      });
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
      const action = (metadata.default_action || 'accept').toLowerCase();
      defaultActionEl.textContent = action;

      // Remove existing color classes
      defaultActionEl.classList.remove('text-green-400', 'text-red-500', 'text-amber-400', 'text-orange-300');

      // Add color based on action
      if (action === 'accept') {
        defaultActionEl.classList.add('text-green-400');
      } else if (action === 'drop') {
        defaultActionEl.classList.add('text-red-500');
      } else if (action === 'reject') {
        defaultActionEl.classList.add('text-amber-400');
      } else {
        defaultActionEl.classList.add('text-orange-300');
      }
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

  function bindRuleActionButtons(handlers) {
    const tbody = document.querySelector(selectors.tableBody);
    if (!tbody || !handlers) return;

    if (handlers.onEdit) {
      tbody.querySelectorAll('.btn-rule-edit').forEach((btn) => {
        btn.addEventListener('click', () => handlers.onEdit(btn.dataset.ruleNumber));
      });
    }
    if (handlers.onDelete) {
      tbody.querySelectorAll('.btn-rule-delete').forEach((btn) => {
        btn.addEventListener('click', () => handlers.onDelete(btn.dataset.ruleNumber));
      });
    }
    if (handlers.onToggle) {
      tbody.querySelectorAll('.btn-rule-disable').forEach((btn) => {
        btn.addEventListener('click', () => handlers.onToggle(btn.dataset.ruleNumber));
      });
    }
  }

  function bindRowDragHandlers(handlers) {
    if (!handlers || !handlers.onReorder) {
      return;
    }
    const rows = document.querySelectorAll('#firewallRulesBody tr');
    const dragState = fwState.dragState || { index: null };

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
        handlers.onReorder(newOrder);
        clearDropTargets();
      });

      row.addEventListener('dragleave', (event) => {
        if (!row.contains(event.relatedTarget)) {
          row.classList.remove('firewall-drop-target');
        }
      });
    });
  }

  function renderRules(handlers) {
    const tbody = document.querySelector(selectors.tableBody);
    if (!tbody) {
      return;
    }

    clearDropTargets();

    const rules = state.rules || [];
    if (!rules.length) {
      renderEmptyRules(tbody);
      bindRuleActionButtons(handlers);
      return;
    }

    const canDrag = rules.length > 1;
    const groupsDetails = state.groupsDetails || {};
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
      const sourceDisplay = formatGroupDisplay(rule.source, groupsDetails);
      const sourcePortDisplay = formatGroupDisplay(rule.source_port, groupsDetails);
      const destinationDisplay = formatGroupDisplay(rule.destination, groupsDetails);
      const destinationPortDisplay = formatGroupDisplay(rule.destination_port, groupsDetails);
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
            ${100 + index}
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
    bindRuleActionButtons(handlers);
    if (canDrag) {
      bindRowDragHandlers(handlers);
    }
  }

  function applyOrderDirtyState(flag) {
    const controls = fwState.reorderControls || {};
    const spinner = fwState.reorderSpinner;
    const saveLabel = fwState.reorderSaveLabel;

    if (controls.container) {
      controls.container.classList.toggle('hidden', !flag);
    }
    if (controls.save) {
      controls.save.disabled = !flag;
    }
    if (controls.cancel) {
      controls.cancel.disabled = !flag;
    }
    if (spinner) {
      spinner.classList.add('hidden');
    }
    if (saveLabel) {
      saveLabel.textContent = 'Save Order';
    }
    updateAddButtonState();
  }

  firewallNs.view = {
    renderZoneList,
    renderPairList,
    renderMetadata,
    renderRules,
    highlightZone,
    updateAddButtonState,
    applyOrderDirtyState,
  };
})(window);

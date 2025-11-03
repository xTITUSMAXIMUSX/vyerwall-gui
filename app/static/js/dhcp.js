/* DHCP configuration UI with modern animations and interactions */

(function () {
  const form = document.getElementById('dhcpForm');
  if (!form) return;

  const elements = {
    form,
    initialState: document.getElementById('initial-state'),
    loadingOverlay: document.getElementById('loading-overlay'),
    panels: Array.from(document.querySelectorAll('[data-dhcp-panel]')),
    tabButtons: Array.from(document.querySelectorAll('[data-dhcp-tab]')),
    scope: {
      sharedNetwork: document.getElementById('sharedNetwork'),
      subnet: document.getElementById('subnet'),
      subnetId: document.getElementById('subnetId'),
      defaultRouter: document.getElementById('defaultRouter'),
      domainName: document.getElementById('subnetDomainName'),
      dnsServers: document.getElementById('subnetNameServers'),
      searchDomains: document.getElementById('subnetDomainSearch'),
      excludes: document.getElementById('subnetExcludeAddresses'),
      startAddress: document.getElementById('startAddress'),
      endAddress: document.getElementById('endAddress'),
      lease: document.getElementById('lease'),
      enableDhcp: document.getElementById('enableDhcp'),
      authoritative: document.getElementById('sharedAuthoritative'),
    },
    staticMappings: document.querySelector('[data-static-mappings]'),
    global: {
      hostfileUpdate: document.getElementById('globalHostfileUpdate'),
      listenAddresses: document.getElementById('globalListenAddresses'),
      haMode: document.getElementById('haMode'),
      haStatus: document.getElementById('haStatus'),
      haSource: document.getElementById('haSource'),
      haRemote: document.getElementById('haRemote'),
      haName: document.getElementById('haName'),
    },
    leasesContainer: document.getElementById('leasesContainer'),
    refreshLeases: document.getElementById('refreshLeases'),
    saveButton: document.getElementById('dhcpSaveButton'),
    saveSpinner: document.getElementById('dhcpSaveSpinner'),
    saveLabel: document.getElementById('dhcpSaveLabel'),
    ifaceTitle: document.getElementById('ifaceTitle'),
    interfaceStatus: document.getElementById('interface-status'),
    interfaceButtons: Array.from(document.querySelectorAll('.select-interface')),
  };

  const state = {
    selectedInterface: null,
    original: null,
  };

  /* ------------------------------------------------------------------
   * Utility helpers
   * ---------------------------------------------------------------- */
  function showNotification(message, type = 'info') {
    const colors = {
      success: 'bg-green-500',
      error: 'bg-red-500',
      info: 'bg-blue-500',
      warning: 'bg-yellow-500',
    };

    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-4 rounded-xl shadow-2xl z-50 transform transition-all duration-300 flex items-center gap-3`;
    notification.style.opacity = '0';
    notification.style.transform = 'translateY(-20px)';

    const icon = {
      success: 'check_circle',
      error: 'error',
      info: 'info',
      warning: 'warning',
    }[type];

    notification.innerHTML = `
      <span class="material-icons">${icon}</span>
      <span>${message}</span>
    `;

    document.body.appendChild(notification);

    requestAnimationFrame(() => {
      notification.style.opacity = '1';
      notification.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
      notification.style.opacity = '0';
      notification.style.transform = 'translateY(-20px)';
      setTimeout(() => notification.remove(), 300);
    }, 4000);
  }

  function toggleButtonLoading(button, spinner, label, isLoading, idleText, busyText) {
    if (!button || !label) return;
    if (isLoading) {
      button.disabled = true;
      button.classList.add('opacity-70', 'cursor-not-allowed');
      if (spinner) spinner.classList.remove('hidden');
      label.textContent = busyText;
    } else {
      button.disabled = false;
      button.classList.remove('opacity-70', 'cursor-not-allowed');
      if (spinner) spinner.classList.add('hidden');
      label.textContent = idleText;
    }
  }

  function setListValue(element, values) {
    if (!element) return;
    const list = Array.isArray(values) ? values : [];
    element.value = list.length ? list.join('\n') : '';
  }

  function getListValue(element) {
    if (!element) return [];
    return (element.value || '')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function showLoading() {
    if (elements.loadingOverlay) {
      elements.loadingOverlay.classList.remove('hidden');
      elements.loadingOverlay.style.opacity = '0';
      requestAnimationFrame(() => {
        elements.loadingOverlay.style.opacity = '1';
        elements.loadingOverlay.style.transition = 'opacity 0.2s ease-out';
      });
    }
  }

  function hideLoading() {
    if (elements.loadingOverlay) {
      elements.loadingOverlay.style.opacity = '0';
      setTimeout(() => {
        elements.loadingOverlay.classList.add('hidden');
      }, 200);
    }
  }

  function showForm() {
    if (elements.initialState) {
      elements.initialState.style.opacity = '0';
      setTimeout(() => {
        elements.initialState.classList.add('hidden');
        form.classList.remove('hidden');
        form.style.opacity = '0';
        requestAnimationFrame(() => {
          form.style.opacity = '1';
          form.style.transition = 'opacity 0.3s ease-out';
        });
      }, 200);
    } else {
      form.classList.remove('hidden');
    }
  }

  /* ------------------------------------------------------------------
   * Tab handling with animations
   * ---------------------------------------------------------------- */
  function activateTab(target) {
    elements.tabButtons.forEach((button) => {
      const isActive = button.dataset.dhcpTab === target;

      if (isActive) {
        button.classList.add('text-blue-400', 'border-blue-500', 'bg-blue-500/10');
        button.classList.remove('text-gray-400', 'border-transparent');
      } else {
        button.classList.remove('text-blue-400', 'border-blue-500', 'bg-blue-500/10');
        button.classList.add('text-gray-400', 'border-transparent');
      }
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    elements.panels.forEach((panel) => {
      const isActive = panel.dataset.dhcpPanel === target;
      if (isActive) {
        panel.classList.remove('hidden');
        panel.style.opacity = '0';
        requestAnimationFrame(() => {
          panel.style.opacity = '1';
          panel.style.transition = 'opacity 0.2s ease-out';
        });
      } else {
        panel.classList.add('hidden');
      }
    });
  }

  function registerTabHandlers() {
    elements.tabButtons.forEach((button) => {
      button.addEventListener('click', () => {
        if (button.dataset.dhcpTab) activateTab(button.dataset.dhcpTab);
      });
    });
    activateTab('scope');
  }

  /* ------------------------------------------------------------------
   * Static mappings with improved visuals
   * ---------------------------------------------------------------- */
  function createStaticMappingRow(entry = {}) {
    const row = document.createElement('div');
    row.className = 'bg-gray-800/50 border border-gray-700 rounded-xl p-4 space-y-3 animate-slide-in hover:bg-gray-800/70 transition-all';
    row.dataset.staticRow = 'true';
    row.innerHTML = `
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-semibold text-gray-300">Static Reservation</h4>
        <button type="button" class="p-1 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-all" data-action="remove-static">
          <span class="material-icons text-sm">delete</span>
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input type="text" data-field="name" class="px-3 py-2 rounded-lg bg-gray-700/50 text-white border border-gray-600 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 focus:outline-none text-sm transition-all" placeholder="Name *" value="${entry.name || ''}">
        <input type="text" data-field="mac" class="px-3 py-2 rounded-lg bg-gray-700/50 text-white border border-gray-600 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 focus:outline-none text-sm font-mono transition-all" placeholder="MAC Address" value="${entry.mac || ''}">
        <input type="text" data-field="ipAddress" class="px-3 py-2 rounded-lg bg-gray-700/50 text-white border border-gray-600 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 focus:outline-none text-sm font-mono transition-all" placeholder="IP Address" value="${entry.ipAddress || ''}">
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <input type="text" data-field="hostname" class="px-3 py-2 rounded-lg bg-gray-700/50 text-white border border-gray-600 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 focus:outline-none text-sm transition-all" placeholder="Hostname (optional)" value="${entry.hostname || ''}">
        <input type="text" data-field="duid" class="px-3 py-2 rounded-lg bg-gray-700/50 text-white border border-gray-600 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 focus:outline-none text-sm font-mono transition-all" placeholder="DUID (optional)" value="${entry.duid || ''}">
      </div>
      <p class="text-xs text-gray-500 italic">Provide either MAC or DUID. IP should be outside the dynamic range.</p>
    `;
    return row;
  }

  function renderStaticMappings(mappings) {
    const list = elements.staticMappings.querySelector('[data-static-list]');
    const emptyState = elements.staticMappings.querySelector('[data-empty-state]');
    if (!list) return;

    list.innerHTML = '';
    (mappings || []).forEach((mapping) => list.appendChild(createStaticMappingRow(mapping)));

    if (emptyState) {
      emptyState.style.display = mappings && mappings.length > 0 ? 'none' : 'block';
    }
  }

  function readStaticMappings() {
    const list = elements.staticMappings.querySelector('[data-static-list]');
    if (!list) return [];
    return Array.from(list.querySelectorAll('[data-static-row]')).map((row) => {
      const entry = {};
      row.querySelectorAll('[data-field]').forEach((input) => {
        const key = input.dataset.field;
        const value = input.value.trim();
        if (key && value) entry[key] = value;
      });
      return entry;
    }).filter((entry) => entry.name);
  }

  function registerStaticMappingHandlers() {
    elements.staticMappings.addEventListener('click', (event) => {
      const trigger = event.target.closest('button');
      if (!trigger) return;

      if (trigger.dataset.action === 'add-static-mapping') {
        const list = elements.staticMappings.querySelector('[data-static-list]');
        const emptyState = elements.staticMappings.querySelector('[data-empty-state]');
        if (list) {
          const newRow = createStaticMappingRow();
          list.appendChild(newRow);
          if (emptyState) emptyState.style.display = 'none';
        }
      }

      if (trigger.dataset.action === 'remove-static') {
        const row = trigger.closest('[data-static-row]');
        if (row) {
          row.style.opacity = '0';
          row.style.transform = 'scale(0.95)';
          row.style.transition = 'all 0.2s ease-out';
          setTimeout(() => {
            row.remove();
            const list = elements.staticMappings.querySelector('[data-static-list]');
            const emptyState = elements.staticMappings.querySelector('[data-empty-state]');
            if (list && emptyState && list.children.length === 0) {
              emptyState.style.display = 'block';
            }
          }, 200);
        }
      }
    });
  }

  /* ------------------------------------------------------------------
   * Form <-> payload transformations
   * ---------------------------------------------------------------- */
  function applyStateToForm(payload) {
    const scope = payload || {};
    const globalSettings = scope.globalSettings || {};
    const staticMappings = scope.staticMappings || [];

    elements.scope.sharedNetwork.value = scope.sharedNetwork || '';
    elements.scope.subnet.value = scope.subnet || '';
    elements.scope.subnetId.value = scope.subnetId || scope.nextAvailableSubnetId || form.dataset.nextSubnetId || '';
    elements.scope.defaultRouter.value = scope.defaultRouter || '';
    elements.scope.domainName.value = scope.domainName || '';
    setListValue(elements.scope.dnsServers, scope.dnsServers || []);
    setListValue(elements.scope.searchDomains, scope.searchDomains || []);
    setListValue(elements.scope.excludes, scope.excludes || []);
    elements.scope.startAddress.value = scope.startAddress || '';
    elements.scope.endAddress.value = scope.endAddress || '';
    elements.scope.lease.value = scope.lease || '86400';
    elements.scope.enableDhcp.checked = Boolean(scope.enabled);
    elements.scope.authoritative.checked = Boolean(scope.authoritative);

    renderStaticMappings(staticMappings);

    elements.global.hostfileUpdate.checked = Boolean(globalSettings.hostfileUpdate);
    setListValue(elements.global.listenAddresses, globalSettings.listenAddresses || []);
    elements.global.haMode.value = globalSettings.highAvailability?.mode || '';
    elements.global.haStatus.value = globalSettings.highAvailability?.status || '';
    elements.global.haSource.value = globalSettings.highAvailability?.['source-address'] || globalSettings.highAvailability?.source_address || '';
    elements.global.haRemote.value = globalSettings.highAvailability?.remote || globalSettings.highAvailability?.remoteAddress || '';
    elements.global.haName.value = globalSettings.highAvailability?.name || '';

    state.original = {
      isConfigured: Boolean(scope.isConfigured),
      sharedNetwork: scope.sharedNetwork || '',
      subnet: scope.subnet || '',
      subnetId: elements.scope.subnetId.value || '',
      defaultRouter: elements.scope.defaultRouter.value || '',
      domainName: elements.scope.domainName.value || '',
      dnsServers: getListValue(elements.scope.dnsServers),
      searchDomains: getListValue(elements.scope.searchDomains),
      excludes: getListValue(elements.scope.excludes),
      startAddress: elements.scope.startAddress.value || '',
      endAddress: elements.scope.endAddress.value || '',
      lease: elements.scope.lease.value || '86400',
      authoritative: elements.scope.authoritative.checked,
      enabled: elements.scope.enableDhcp.checked,
      staticMappings: staticMappings.map((entry) => ({ ...entry })),
    };

    state.original.global = JSON.parse(JSON.stringify(globalSettings || {}));

    // Update interface status
    if (elements.interfaceStatus) {
      if (scope.isConfigured) {
        elements.interfaceStatus.textContent = 'DHCP Configured';
        elements.interfaceStatus.parentElement.querySelector('.material-icons').textContent = 'check_circle';
        elements.interfaceStatus.classList.remove('text-gray-400');
        elements.interfaceStatus.classList.add('text-green-400');
      } else {
        elements.interfaceStatus.textContent = 'Not configured';
        elements.interfaceStatus.parentElement.querySelector('.material-icons').textContent = 'error';
        elements.interfaceStatus.classList.remove('text-green-400');
        elements.interfaceStatus.classList.add('text-gray-400');
      }
    }

    showForm();
  }

  function getFormValues() {
    const sharedNetwork = (elements.scope.sharedNetwork.value || '').trim();
    const subnetValue = (elements.scope.subnet.value || '').trim();
    const subnetIdValue = (elements.scope.subnetId.value || '').trim();

    if (!sharedNetwork) throw new Error('Shared network name is required.');
    if (!subnetValue) throw new Error('Subnet value is required.');

    const dnsServers = getListValue(elements.scope.dnsServers);
    if (!dnsServers.length) throw new Error('Provide at least one DNS server.');

    const scopeData = {
      sharedNetwork,
      subnet: subnetValue,
      subnetId: subnetIdValue,
      defaultRouter: (elements.scope.defaultRouter.value || '').trim(),
      domainName: (elements.scope.domainName.value || '').trim(),
      dnsServers,
      searchDomains: getListValue(elements.scope.searchDomains),
      excludes: getListValue(elements.scope.excludes),
      startAddress: (elements.scope.startAddress.value || '').trim(),
      endAddress: (elements.scope.endAddress.value || '').trim(),
      lease: (elements.scope.lease.value || '').trim(),
      authoritative: elements.scope.authoritative.checked,
      enabled: elements.scope.enableDhcp.checked,
      staticMappings: readStaticMappings(),
    };

    const haSettings = {};
    if (elements.global.haMode.value) haSettings.mode = elements.global.haMode.value;
    if (elements.global.haStatus.value) haSettings.status = elements.global.haStatus.value;
    const sourceValue = (elements.global.haSource.value || '').trim();
    if (sourceValue) haSettings['source-address'] = sourceValue;
    const remoteValue = (elements.global.haRemote.value || '').trim();
    if (remoteValue) haSettings.remote = remoteValue;
    const nameValue = (elements.global.haName.value || '').trim();
    if (nameValue) haSettings.name = nameValue;

    return {
      data: scopeData,
      global: {
        hostfileUpdate: elements.global.hostfileUpdate.checked,
        listenAddresses: getListValue(elements.global.listenAddresses),
        highAvailability: haSettings,
      },
    };
  }

  /* ------------------------------------------------------------------
   * Networking helpers
   * ---------------------------------------------------------------- */
  async function fetchLeases(iface) {
    if (!iface) {
      elements.leasesContainer.innerHTML = '<div class="text-center py-12 text-gray-500"><span class="material-icons text-5xl mb-3 opacity-50">receipt</span><p class="text-sm">Select an interface to view leases</p></div>';
      return;
    }

    elements.leasesContainer.innerHTML = '<div class="text-center py-8"><span class="material-icons text-4xl text-blue-400 animate-spin">refresh</span><p class="text-sm text-gray-400 mt-2">Loading leases...</p></div>';

    try {
      const response = await fetch(`/services/dhcp/${iface}/leases`);
      if (!response.ok) throw new Error('Failed to load leases.');
      const payload = await response.json();
      const leases = payload.data || [];

      if (!leases.length) {
        elements.leasesContainer.innerHTML = '<div class="text-center py-12 text-gray-500"><span class="material-icons text-5xl mb-3 opacity-50">receipt_long</span><p class="text-sm">No active leases</p></div>';
        return;
      }

      const fragment = document.createDocumentFragment();
      leases.forEach((lease, index) => {
        const card = document.createElement('div');
        card.className = 'bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:bg-gray-800/70 transition-all animate-slide-in';
        card.style.animationDelay = `${index * 0.05}s`;
        card.innerHTML = `
          <div class="flex items-center justify-between mb-3">
            <span class="font-mono text-lg font-semibold text-blue-400">${lease.ip || '—'}</span>
            <span class="text-xs px-2 py-1 rounded-full ${lease.state === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}">${lease.state || 'unknown'}</span>
          </div>
          <div class="space-y-1.5 text-xs">
            <div class="flex justify-between text-gray-400">
              <span>MAC</span>
              <span class="font-mono text-gray-300">${lease.mac || '—'}</span>
            </div>
            <div class="flex justify-between text-gray-400">
              <span>Hostname</span>
              <span class="text-gray-300">${lease.hostname || '—'}</span>
            </div>
            <div class="flex justify-between text-gray-400">
              <span>Expires</span>
              <span class="text-gray-300">${lease.lease_expiration || '—'}</span>
            </div>
            ${lease.remaining ? `<div class="flex justify-between text-gray-400"><span>Remaining</span><span class="text-gray-300">${lease.remaining}</span></div>` : ''}
          </div>
        `;
        fragment.appendChild(card);
      });

      elements.leasesContainer.innerHTML = '';
      elements.leasesContainer.appendChild(fragment);
    } catch (error) {
      console.error(error);
      elements.leasesContainer.innerHTML = '<div class="text-center py-12 text-red-400"><span class="material-icons text-5xl mb-3 opacity-50">error</span><p class="text-sm">Failed to load leases</p></div>';
    }
  }

  async function fetchInterfaceDhcp(iface, description) {
    // Show loading overlay
    showLoading();

    elements.ifaceTitle.textContent = `DHCP Settings for ${iface}`;

    try {
      const response = await fetch(`/services/dhcp/${iface}`);
      if (!response.ok) throw new Error('Unable to load DHCP configuration.');
      const data = await response.json();

      // Apply state to form (this will update all fields)
      applyStateToForm(data);
      state.selectedInterface = iface;

      // Fetch leases
      await fetchLeases(iface);

      // Highlight selected interface
      elements.interfaceButtons.forEach(btn => {
        if (btn.dataset.iface === iface) {
          btn.classList.add('bg-gray-700/50', 'border-blue-500');
        } else {
          btn.classList.remove('bg-gray-700/50', 'border-blue-500');
        }
      });

      // Hide loading overlay
      hideLoading();
    } catch (error) {
      hideLoading();
      console.error(error);
      showNotification(error.message || 'Failed to load DHCP configuration.', 'error');
    }
  }

  async function saveConfiguration(payload) {
    if (!state.selectedInterface) {
      showNotification('Please choose an interface first.', 'warning');
      return;
    }

    const endpoint = state.original?.isConfigured
      ? `/services/dhcp/${state.selectedInterface}/update`
      : `/services/dhcp/${state.selectedInterface}/create`;

    const body = {
      data: payload.data,
      global: payload.global,
      original: state.original || {},
    };

    try {
      toggleButtonLoading(elements.saveButton, elements.saveSpinner, elements.saveLabel, true, 'Save Configuration', 'Saving...');
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = await response.json();

      if (!response.ok || result.status !== 'ok') {
        throw new Error(result.message || 'Failed to save DHCP configuration.');
      }

      // Update the unsaved changes banner if config_dirty flag is present
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      applyStateToForm(result.data || {});
      await fetchLeases(state.selectedInterface);
      showNotification('DHCP configuration saved successfully!', 'success');
    } catch (error) {
      console.error(error);
      showNotification(error.message || 'Failed to save DHCP configuration.', 'error');
    } finally {
      toggleButtonLoading(elements.saveButton, elements.saveSpinner, elements.saveLabel, false, 'Save Configuration', 'Saving...');
    }
  }

  /* ------------------------------------------------------------------
   * Event wiring
   * ---------------------------------------------------------------- */
  function registerInterfaceHandlers() {
    elements.interfaceButtons.forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          await fetchInterfaceDhcp(button.dataset.iface, button.dataset.description);
        } catch (error) {
          console.error(error);
          showNotification(error.message || 'Failed to load DHCP configuration.', 'error');
        }
      });
    });
  }

  function registerFormHandler() {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
        if (typeof form.reportValidity === 'function') form.reportValidity();
        return;
      }

      let payload;
      try {
        payload = getFormValues();
      } catch (error) {
        showNotification(error.message || 'Invalid form data.', 'error');
        return;
      }

      await saveConfiguration(payload);
    });
  }

  function registerLeasesRefresh() {
    if (elements.refreshLeases) {
      elements.refreshLeases.addEventListener('click', async () => {
        if (!state.selectedInterface) return;
        await fetchLeases(state.selectedInterface);
      });
    }
  }

  /* ------------------------------------------------------------------
   * Initialize
   * ---------------------------------------------------------------- */
  function init() {
    registerTabHandlers();
    registerStaticMappingHandlers();
    registerInterfaceHandlers();
    registerLeasesRefresh();
    registerFormHandler();
  }

  init();
})();

const api = {
  overview: '/firewall/zones/api/overview',
  create: '/firewall/zones/api/create',
  delete: '/firewall/zones/api/delete',
  membership: '/firewall/zones/api/membership',
};

const data = window.FIREWALL_ZONE_DATA || {};

const els = {
  createModal: document.getElementById('zoneCreateModal'),
  createForm: document.getElementById('zoneCreateForm'),
  createInterface: document.getElementById('createZoneInterface'),
  createSubmit: document.getElementById('zoneCreateSubmit'),
  createSpinner: document.getElementById('zoneCreateSpinner'),
  createLabel: document.getElementById('zoneCreateLabel'),
  createIcon: document.getElementById('zoneCreateIcon'),
  openCreateBtn: document.getElementById('openCreateZone'),

  deleteModal: document.getElementById('zoneDeleteModal'),
  deleteMessage: document.getElementById('zoneDeleteMessage'),
  deleteConfirm: document.getElementById('zoneDeleteConfirm'),
  deleteSpinner: document.getElementById('zoneDeleteSpinner'),
  deleteLabel: document.getElementById('zoneDeleteLabel'),
  deleteIcon: document.getElementById('zoneDeleteIcon'),

  manageModal: document.getElementById('zoneManageModal'),
  manageZoneName: document.getElementById('manageZoneName'),
  manageMembers: document.getElementById('manageZoneMembers'),
  addMemberForm: document.getElementById('zoneAddMemberForm'),
  addMemberSelect: document.getElementById('zoneAddInterface'),
  addMemberSubmit: document.getElementById('zoneAddMemberSubmit'),
  addMemberSpinner: document.getElementById('zoneAddMemberSpinner'),
  addMemberLabel: document.getElementById('zoneAddMemberLabel'),
  addMemberIcon: document.getElementById('zoneAddMemberIcon'),

  toastContainer: document.getElementById('toastContainer'),
};

let activeZone = null;

// Toast notification system
function showToast(message, type = 'info') {
  const colors = {
    success: { bg: 'from-green-600 to-emerald-600', icon: 'check_circle', iconColor: 'text-green-300' },
    error: { bg: 'from-red-600 to-red-700', icon: 'error', iconColor: 'text-red-300' },
    info: { bg: 'from-blue-600 to-purple-600', icon: 'info', iconColor: 'text-blue-300' },
    warning: { bg: 'from-orange-500 to-red-600', icon: 'warning', iconColor: 'text-orange-300' },
  };

  const config = colors[type] || colors.info;
  const toast = document.createElement('div');
  toast.className = `flex items-center gap-3 bg-gradient-to-r ${config.bg} text-white px-5 py-4 rounded-xl shadow-2xl border border-white/20 transform transition-all duration-300 opacity-0 translate-x-full min-w-[320px]`;
  toast.innerHTML = `
    <span class="material-icons ${config.iconColor}">${config.icon}</span>
    <span class="flex-1 font-medium">${message}</span>
    <button class="material-icons text-sm hover:scale-110 transition-transform opacity-70 hover:opacity-100" onclick="this.parentElement.remove()">close</button>
  `;

  if (els.toastContainer) {
    els.toastContainer.appendChild(toast);
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(0)';
    });

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }
}

function toggleButtonLoading(button, spinner, icon, label, isLoading, idleText, busyText) {
  if (!button || !label) return;
  if (isLoading) {
    button.disabled = true;
    button.classList.add('opacity-70', 'cursor-not-allowed');
    if (spinner) spinner.classList.remove('hidden');
    if (icon) icon.classList.add('hidden');
    label.textContent = busyText;
  } else {
    button.disabled = false;
    button.classList.remove('opacity-70', 'cursor-not-allowed');
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
    label.textContent = idleText;
  }
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.add('hidden');
}

function openModal(modal) {
  if (!modal) return;
  modal.classList.remove('hidden');
}

function populateCreateInterfaceOptions() {
  if (!els.createInterface) return;
  const options = (data.unassigned_interfaces || []).map((iface) => {
    return `<option value="${iface}">${iface}</option>`;
  }).join('');
  els.createInterface.innerHTML = `<option value="">Select interface...</option>${options}`;
}

function handleCreateZone(event) {
  event.preventDefault();
  const form = new FormData(els.createForm);
  const payload = {
    zone: form.get('zone')?.trim(),
    interface: form.get('interface')?.trim(),
  };
  if (!payload.zone || !payload.interface) {
    showToast('Zone name and interface are required', 'warning');
    return;
  }

  toggleButtonLoading(els.createSubmit, els.createSpinner, els.createIcon, els.createLabel, true, 'Create Zone', 'Creating...');
  fetch(api.create, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then((res) => {
      if (res.status !== 'ok') {
        throw new Error(res.message || 'Failed to create zone');
      }
      showToast(`Zone "${payload.zone}" created successfully!`, 'success');
      setTimeout(() => window.location.reload(), 1000);
    })
    .catch((err) => {
      console.error(err);
      showToast(err.message || 'Failed to create zone', 'error');
      toggleButtonLoading(els.createSubmit, els.createSpinner, els.createIcon, els.createLabel, false, 'Create Zone', 'Creating...');
    });
}

function openDeleteModal(zone) {
  activeZone = zone;
  if (els.deleteMessage) {
    els.deleteMessage.innerHTML = `Delete zone <span class="font-semibold text-red-400">${zone}</span>?`;
  }
  openModal(els.deleteModal);
}

function handleDeleteZone() {
  if (!activeZone) return;
  toggleButtonLoading(els.deleteConfirm, els.deleteSpinner, els.deleteIcon, els.deleteLabel, true, 'Delete', 'Deleting...');
  fetch(api.delete, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone: activeZone }),
  })
    .then((res) => res.json())
    .then((res) => {
      if (res.status !== 'ok') {
        throw new Error(res.message || 'Failed to delete zone');
      }
      showToast(`Zone "${activeZone}" deleted successfully`, 'success');
      setTimeout(() => window.location.reload(), 1000);
    })
    .catch((err) => {
      console.error(err);
      showToast(err.message || 'Failed to delete zone', 'error');
      toggleButtonLoading(els.deleteConfirm, els.deleteSpinner, els.deleteIcon, els.deleteLabel, false, 'Delete', 'Deleting...');
    });
}

function renderMemberBadges(zone, members) {
  if (!els.manageMembers) return;
  els.manageMembers.innerHTML = '';
  if (!members || !members.length) {
    els.manageMembers.innerHTML = '<div class="flex items-center gap-2 text-xs text-gray-500 italic p-2"><span class="material-icons text-xs">info</span>No interfaces assigned</div>';
    return;
  }
  members.forEach((iface) => {
    const badge = document.createElement('button');
    badge.className = 'group inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-gray-700 to-gray-800 hover:from-red-600 hover:to-red-700 border border-gray-600 hover:border-red-500 text-xs rounded-lg text-white font-medium transition-all shadow hover:shadow-lg zone-remove-member';
    badge.dataset.interface = iface;
    badge.dataset.zone = zone;
    badge.innerHTML = `
      <span class="material-icons text-xs text-cyan-400 group-hover:text-white">settings_ethernet</span>
      <span>${iface}</span>
      <span class="material-icons text-xs opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-transform">close</span>
    `;
    els.manageMembers.appendChild(badge);
  });
}

function populateAddMemberOptions(exclude = []) {
  if (!els.addMemberSelect) return;
  const available = (data.unassigned_interfaces || []).filter((iface) => !exclude.includes(iface));
  if (!available.length) {
    els.addMemberSelect.innerHTML = '<option value="">No unassigned interfaces</option>';
    els.addMemberSelect.disabled = true;
  } else {
    els.addMemberSelect.disabled = false;
    els.addMemberSelect.innerHTML = ['<option value="">Select interface...</option>', ...available.map((iface) => `<option value="${iface}">${iface}</option>`)].join('');
  }
}

function openManageModal(zone, membersJson) {
  activeZone = zone;
  let members = [];
  try {
    members = JSON.parse(membersJson) || [];
  } catch (err) {
    members = [];
  }
  if (els.manageZoneName) {
    els.manageZoneName.textContent = zone;
  }
  renderMemberBadges(zone, members);
  populateAddMemberOptions(members);
  openModal(els.manageModal);
}

function handleAddMember(event) {
  event.preventDefault();
  if (!activeZone) return;
  const iface = els.addMemberSelect?.value;
  if (!iface) {
    showToast('Select an interface to add', 'warning');
    return;
  }
  toggleButtonLoading(els.addMemberSubmit, els.addMemberSpinner, els.addMemberIcon, els.addMemberLabel, true, 'Add Interface', 'Adding...');
  fetch(api.membership, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone: activeZone, interface: iface, action: 'add' }),
  })
    .then((res) => res.json())
    .then((res) => {
      if (res.status !== 'ok') {
        throw new Error(res.message || 'Failed to add interface.');
      }
      showToast(`Interface "${iface}" added to zone "${activeZone}"`, 'success');
      setTimeout(() => window.location.reload(), 1000);
    })
    .catch((err) => {
      console.error(err);
      showToast(err.message || 'Failed to add interface to zone', 'error');
      toggleButtonLoading(els.addMemberSubmit, els.addMemberSpinner, els.addMemberIcon, els.addMemberLabel, false, 'Add Interface', 'Adding...');
    });
}

function handleRemoveMember(event) {
  const btn = event.target.closest('.zone-remove-member');
  if (!btn) return;
  const zone = btn.dataset.zone;
  const iface = btn.dataset.interface;
  if (!zone || !iface) return;

  // Add loading state to button
  btn.disabled = true;
  btn.classList.add('opacity-50', 'cursor-not-allowed');

  fetch(api.membership, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone, interface: iface, action: 'remove' }),
  })
    .then((res) => res.json())
    .then((res) => {
      if (res.status !== 'ok') {
        throw new Error(res.message || 'Failed to remove interface.');
      }
      showToast(`Interface "${iface}" removed from zone "${zone}"`, 'success');
      setTimeout(() => window.location.reload(), 1000);
    })
    .catch((err) => {
      console.error(err);
      showToast(err.message || 'Failed to remove interface from zone', 'error');
      btn.disabled = false;
      btn.classList.remove('opacity-50', 'cursor-not-allowed');
    });
}

function bindMatrixNavigation() {
  document.querySelectorAll('.zone-matrix-cell').forEach((btn) => {
    btn.addEventListener('click', () => {
      const source = btn.dataset.source;
      const destination = btn.dataset.destination;
      const firewall = btn.dataset.firewall;
      if (firewall) {
        window.location.href = `${'/firewall/rules'}?firewall=${encodeURIComponent(firewall)}&source=${encodeURIComponent(source)}&dest=${encodeURIComponent(destination)}`;
      }
    });
  });
}

function bindZoneDirectoryActions() {
  document.querySelectorAll('.zone-delete-btn').forEach((btn) => {
    btn.addEventListener('click', () => openDeleteModal(btn.dataset.zone));
  });
  document.querySelectorAll('.zone-manage-btn').forEach((btn) => {
    btn.addEventListener('click', () => openManageModal(btn.dataset.zone, btn.dataset.members || '[]'));
  });
}

function bindModalCloseControls() {
  document.querySelectorAll('[data-zone-modal-close]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.getAttribute('data-zone-modal-close');
      if (target === 'create') closeModal(els.createModal);
      if (target === 'delete') closeModal(els.deleteModal);
      if (target === 'manage') closeModal(els.manageModal);
    });
  });
  [els.createModal, els.deleteModal, els.manageModal].forEach((modal) => {
    if (!modal) return;
    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal(modal);
    });
  });
}

function init() {
  if (els.openCreateBtn) {
    els.openCreateBtn.addEventListener('click', () => {
      populateCreateInterfaceOptions();
      openModal(els.createModal);
      setTimeout(() => document.getElementById('createZoneName')?.focus(), 50);
    });
  }
  if (els.createForm) {
    els.createForm.addEventListener('submit', handleCreateZone);
  }
  if (els.deleteConfirm) {
    els.deleteConfirm.addEventListener('click', handleDeleteZone);
  }
  if (els.addMemberForm) {
    els.addMemberForm.addEventListener('submit', handleAddMember);
  }
  if (els.manageMembers) {
    els.manageMembers.addEventListener('click', handleRemoveMember);
  }

  bindModalCloseControls();
  bindZoneDirectoryActions();
  bindMatrixNavigation();
}

document.addEventListener('DOMContentLoaded', init);

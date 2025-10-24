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
  openCreateBtn: document.getElementById('openCreateZone'),

  deleteModal: document.getElementById('zoneDeleteModal'),
  deleteMessage: document.getElementById('zoneDeleteMessage'),
  deleteConfirm: document.getElementById('zoneDeleteConfirm'),
  deleteSpinner: document.getElementById('zoneDeleteSpinner'),
  deleteLabel: document.getElementById('zoneDeleteLabel'),

  manageModal: document.getElementById('zoneManageModal'),
  manageZoneName: document.getElementById('manageZoneName'),
  manageMembers: document.getElementById('manageZoneMembers'),
  addMemberForm: document.getElementById('zoneAddMemberForm'),
  addMemberSelect: document.getElementById('zoneAddInterface'),
  addMemberSubmit: document.getElementById('zoneAddMemberSubmit'),
  addMemberSpinner: document.getElementById('zoneAddMemberSpinner'),
  addMemberLabel: document.getElementById('zoneAddMemberLabel'),
};

let activeZone = null;

function toggleButtonLoading(button, spinner, label, isLoading, idleText, busyText) {
  if (!button || !label) return;
  if (isLoading) {
    button.disabled = true;
    button.classList.add('opacity-70', 'cursor-not-allowed', 'animate-pulse');
    if (spinner) spinner.classList.remove('hidden');
    label.textContent = busyText;
  } else {
    button.disabled = false;
    button.classList.remove('opacity-70', 'cursor-not-allowed', 'animate-pulse');
    if (spinner) spinner.classList.add('hidden');
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
    alert('Zone name and interface are required.');
    return;
  }

  toggleButtonLoading(els.createSubmit, els.createSpinner, els.createLabel, true, 'Create Zone', 'Creating...');
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
      window.location.reload();
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to create zone.');
    })
    .finally(() => {
      toggleButtonLoading(els.createSubmit, els.createSpinner, els.createLabel, false, 'Create Zone', 'Creating...');
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
  toggleButtonLoading(els.deleteConfirm, els.deleteSpinner, els.deleteLabel, true, 'Delete', 'Deleting...');
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
      window.location.reload();
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to delete zone.');
    })
    .finally(() => {
      toggleButtonLoading(els.deleteConfirm, els.deleteSpinner, els.deleteLabel, false, 'Delete', 'Deleting...');
    });
}

function renderMemberBadges(zone, members) {
  if (!els.manageMembers) return;
  els.manageMembers.innerHTML = '';
  if (!members || !members.length) {
    els.manageMembers.innerHTML = '<span class="text-xs text-gray-500 italic">No interfaces assigned</span>';
    return;
  }
  members.forEach((iface) => {
    const badge = document.createElement('button');
    badge.className = 'inline-flex items-center gap-1 px-3 py-1 bg-gray-700 hover:bg-red-600 text-xs rounded text-white zone-remove-member';
    badge.dataset.interface = iface;
    badge.dataset.zone = zone;
    badge.innerHTML = `<span class="material-icons text-xs">link_off</span>${iface}`;
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
    alert('Select an interface to add.');
    return;
  }
  toggleButtonLoading(els.addMemberSubmit, els.addMemberSpinner, els.addMemberLabel, true, 'Add Interface', 'Adding...');
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
      window.location.reload();
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to add interface to zone.');
    })
    .finally(() => {
      toggleButtonLoading(els.addMemberSubmit, els.addMemberSpinner, els.addMemberLabel, false, 'Add Interface', 'Adding...');
    });
}

function handleRemoveMember(event) {
  const btn = event.target.closest('.zone-remove-member');
  if (!btn) return;
  const zone = btn.dataset.zone;
  const iface = btn.dataset.interface;
  if (!zone || !iface) return;

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
      window.location.reload();
    })
    .catch((err) => {
      console.error(err);
      alert(err.message || 'Failed to remove interface from zone.');
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

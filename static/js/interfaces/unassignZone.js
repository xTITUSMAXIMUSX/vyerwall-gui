import { requestJson, toggleButtonLoading } from './utils.js';

const modal = document.getElementById('unassignZoneModal');
const messageEl = modal ? document.getElementById('unassignZoneMessage') : null;
const ifaceEl = modal ? document.getElementById('unassignZoneInterface') : null;
const zoneEl = modal ? document.getElementById('unassignZoneZone') : null;
const confirmBtn = modal ? document.getElementById('confirmUnassignZone') : null;
const spinnerEl = modal ? document.getElementById('unassignZoneSpinner') : null;
const submitLabelEl = modal ? document.getElementById('unassignZoneSubmitLabel') : null;

const IDLE_TEXT = 'Remove';
const BUSY_TEXT = 'Removing...';

let activeButton = null;
let modalInitialized = false;
let isSubmitting = false;

export function bindUnassignZoneButtons() {
  if (!modal || !confirmBtn) {
    return;
  }

  initializeModalControls();

  document.querySelectorAll('.unassign-zone-btn').forEach((btn) => {
    btn.addEventListener('click', () => openModal(btn));
  });
}

function initializeModalControls() {
  if (modalInitialized) {
    return;
  }
  modalInitialized = true;

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });

  modal.querySelectorAll('[data-unassign-close]').forEach((el) => {
    el.addEventListener('click', () => closeModal());
  });

  confirmBtn.addEventListener('click', submitUnassign);
}

function openModal(btn) {
  const iface = btn.dataset.iface || '';
  const zone = btn.dataset.zone || '';

  if (!iface) {
    return;
  }
  if (!zone) {
    alert('This interface is not assigned to a zone.');
    return;
  }

  activeButton = btn;
  if (messageEl) {
    messageEl.textContent = `Remove interface ${iface} from zone ${zone}?`;
  }
  if (ifaceEl) {
    ifaceEl.textContent = iface;
  }
  if (zoneEl) {
    zoneEl.textContent = zone;
  }
  if (submitLabelEl) {
    submitLabelEl.textContent = IDLE_TEXT;
  }
  if (spinnerEl) {
    spinnerEl.classList.add('hidden');
  }
  confirmBtn.classList.remove('opacity-70', 'cursor-not-allowed', 'animate-pulse');
  confirmBtn.disabled = false;

  modal.classList.remove('hidden');
  setTimeout(() => {
    confirmBtn.focus();
  }, 0);
}

function closeModal() {
  if (modal) {
    modal.classList.add('hidden');
  }
  toggleButtonLoading(confirmBtn, spinnerEl, submitLabelEl, false, IDLE_TEXT, BUSY_TEXT);
  isSubmitting = false;
  activeButton = null;
}

async function submitUnassign() {
  if (isSubmitting || !activeButton) {
    return;
  }

  const payload = buildPayload(activeButton);
  if (!payload) {
    return;
  }

  const iface = activeButton.dataset.iface;
  if (!iface) {
    return;
  }

  isSubmitting = true;
  toggleButtonLoading(confirmBtn, spinnerEl, submitLabelEl, true, IDLE_TEXT, BUSY_TEXT);

  try {
    const result = await requestJson(`/interfaces/edit/${encodeURIComponent(iface)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (result.status !== 'ok') {
      alert(result.message || 'Failed to remove interface from zone.');
      return;
    }

    const row = activeButton.closest('tr');
    if (row) {
      const zoneBadge = row.querySelector('.iface-zone');
      if (zoneBadge) {
        zoneBadge.textContent = 'Zone: Unassigned';
      }
      const editBtn = row.querySelector('.edit-btn');
      if (editBtn) {
        editBtn.dataset.zone = '';
      }
    }
    activeButton.remove();
    closeModal();
  } catch (error) {
    console.error('Error removing interface from zone:', error);
    alert('Error removing interface from zone.');
  } finally {
    toggleButtonLoading(confirmBtn, spinnerEl, submitLabelEl, false, IDLE_TEXT, BUSY_TEXT);
    isSubmitting = false;
  }
}

function buildPayload(btn) {
  const mode = (btn.dataset.mode || '').toLowerCase();
  let address = btn.dataset.address || '';
  let payloadMode = mode;

  if (mode === 'dhcp') {
    address = 'dhcp';
  }

  if (payloadMode !== 'dhcp' && payloadMode !== 'static') {
    payloadMode = address === 'dhcp' ? 'dhcp' : 'static';
  }

  if (payloadMode === 'static' && (!address || address === 'dhcp')) {
    alert('This interface must have a valid address before removing zone membership.');
    return null;
  }

  return {
    description: btn.dataset.description || '',
    mode: payloadMode,
    address,
    source_nat_interface: btn.dataset.natInterface || '',
    nat_rule_number: btn.dataset.natRule || '',
    zone: '',
  };
}

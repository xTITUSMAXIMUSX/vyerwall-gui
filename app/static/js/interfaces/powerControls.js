import { requestJson, toggleButtonLoading } from './utils.js';

const modal = document.getElementById('togglePowerModal');
const titleEl = modal ? document.getElementById('togglePowerTitle') : null;
const messageEl = modal ? document.getElementById('togglePowerMessage') : null;
const ifaceEl = modal ? document.getElementById('togglePowerInterface') : null;
const stateEl = modal ? document.getElementById('togglePowerState') : null;
const confirmBtn = modal ? document.getElementById('confirmTogglePower') : null;
const spinnerEl = modal ? document.getElementById('togglePowerSpinner') : null;
const submitLabelEl = modal ? document.getElementById('togglePowerSubmitLabel') : null;

let activeButton = null;
let isSubmitting = false;

export function bindPowerControls() {
  if (!modal || !confirmBtn) {
    return;
  }

  initializeModalHandlers();

  document.querySelectorAll('.power-btn').forEach((btn) => {
    btn.addEventListener('click', () => openModal(btn));
  });
}

function initializeModalHandlers() {
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeModal();
    }
  });

  modal.querySelectorAll('[data-toggle-power-close]').forEach((element) => {
    element.addEventListener('click', () => closeModal());
  });

  confirmBtn.addEventListener('click', submitToggle);
}

function openModal(btn) {
  const iface = btn.dataset.iface || '';
  if (!iface) {
    return;
  }

  activeButton = btn;
  const isActive = btn.dataset.state === 'UP';
  const action = isActive ? 'Disable' : 'Enable';
  const busyText = isActive ? 'Disabling...' : 'Enabling...';

  confirmBtn.dataset.busyText = busyText;
  confirmBtn.dataset.idleText = action;
  confirmBtn.dataset.endpoint = isActive
    ? `/interfaces/disable/${encodeURIComponent(iface)}`
    : `/interfaces/enable/${encodeURIComponent(iface)}`;
  confirmBtn.dataset.nextState = isActive ? 'DOWN' : 'UP';

  confirmBtn.classList.toggle('bg-red-600', isActive);
  confirmBtn.classList.toggle('hover:bg-red-700', isActive);
  confirmBtn.classList.toggle('bg-green-600', !isActive);
  confirmBtn.classList.toggle('hover:bg-green-700', !isActive);

  if (titleEl) {
    titleEl.textContent = `${action} Interface`;
  }
  if (messageEl) {
    messageEl.textContent = `${action} interface ${iface}?`;
  }
  if (ifaceEl) {
    ifaceEl.textContent = iface;
  }
  if (stateEl) {
    stateEl.textContent = isActive ? 'Active' : 'Down';
  }
  if (submitLabelEl) {
    submitLabelEl.textContent = action;
  }
  if (spinnerEl) {
    spinnerEl.classList.add('hidden');
  }
  confirmBtn.disabled = false;
  confirmBtn.classList.remove('opacity-70', 'cursor-not-allowed', 'animate-pulse');

  modal.classList.remove('hidden');
  setTimeout(() => confirmBtn.focus(), 0);
}

function closeModal() {
  if (!modal) {
    return;
  }
  modal.classList.add('hidden');
  toggleButtonLoading(
    confirmBtn,
    spinnerEl,
    submitLabelEl,
    false,
    confirmBtn?.dataset.idleText || 'Continue',
    confirmBtn?.dataset.busyText || 'Working...'
  );
  isSubmitting = false;
  activeButton = null;
}

async function submitToggle() {
  if (isSubmitting || !activeButton || !confirmBtn) {
    return;
  }

  const endpoint = confirmBtn.dataset.endpoint;
  if (!endpoint) {
    return;
  }

  isSubmitting = true;
  toggleButtonLoading(
    confirmBtn,
    spinnerEl,
    submitLabelEl,
    true,
    confirmBtn.dataset.idleText || 'Continue',
    confirmBtn.dataset.busyText || 'Working...'
  );

  try {
    const result = await requestJson(endpoint, { method: 'POST' });
    if (result.status !== 'ok') {
      alert(result.message || 'Failed to change interface state.');
      toggleButtonLoading(
        confirmBtn,
        spinnerEl,
        submitLabelEl,
        false,
        confirmBtn.dataset.idleText || 'Continue',
        confirmBtn.dataset.busyText || 'Working...'
      );
      isSubmitting = false;
      return;
    }

    updateRowState(activeButton, confirmBtn.dataset.nextState === 'UP');
    closeModal();
  } catch (error) {
    console.error('Error toggling interface:', error);
    alert('Failed to change interface state.');
    toggleButtonLoading(
      confirmBtn,
      spinnerEl,
      submitLabelEl,
      false,
      confirmBtn.dataset.idleText || 'Continue',
      confirmBtn.dataset.busyText || 'Working...'
    );
    isSubmitting = false;
  }
}

function updateRowState(btn, willBeActive) {
  const row = btn.closest('tr');
  if (!row) {
    return;
  }

  const statusCell = row.querySelector('.iface-status');
  const icon = statusCell ? statusCell.querySelector('.material-icons') : null;
  const textSpan = icon ? icon.nextElementSibling : null;

  if (!icon || !textSpan) {
    return;
  }

  if (willBeActive) {
    icon.classList.remove('text-red-500');
    icon.classList.add('text-green-400');
    icon.textContent = 'check_circle';
    textSpan.classList.remove('text-red-400');
    textSpan.classList.add('text-green-300');
    textSpan.textContent = 'Active';
    btn.dataset.state = 'UP';
  } else {
    icon.classList.remove('text-green-400');
    icon.classList.add('text-red-500');
    icon.textContent = 'cancel';
    textSpan.classList.remove('text-green-300');
    textSpan.classList.add('text-red-400');
    textSpan.textContent = 'Down';
    btn.dataset.state = 'DOWN';
  }
}

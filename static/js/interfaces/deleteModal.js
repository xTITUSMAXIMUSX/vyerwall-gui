import { elements, state } from './domCache.js';
import { requestJson, toggleButtonLoading } from './utils.js';

export function bindDeleteModal() {
  if (!elements.deleteModal) {
    return;
  }

  document.querySelectorAll('.delete-btn').forEach((btn) => {
    btn.addEventListener('click', () => openDeleteModal(btn));
  });

  elements.deleteModal.addEventListener('click', (event) => {
    if (event.target === elements.deleteModal) {
      closeDeleteModal();
    }
  });

  if (elements.deleteCloseButtons && elements.deleteCloseButtons.length) {
    elements.deleteCloseButtons.forEach((btn) => btn.addEventListener('click', closeDeleteModal));
  }

  if (elements.confirmDeleteBtn) {
    elements.confirmDeleteBtn.addEventListener('click', submitDelete);
  }
}

function openDeleteModal(btn) {
  state.deleteTarget = btn.dataset.iface;
  const zone = btn.dataset.zone || 'Unassigned';
  const address = btn.dataset.address || 'N/A';
  const description = btn.dataset.description || 'None';

  if (elements.deleteIfaceName) {
    elements.deleteIfaceName.textContent = state.deleteTarget || '--';
  }
  if (elements.deleteInterfaceValue) {
    elements.deleteInterfaceValue.textContent = state.deleteTarget || '--';
  }
  if (elements.deleteZoneValue) {
    elements.deleteZoneValue.textContent = zone;
  }
  if (elements.deleteAddressValue) {
    elements.deleteAddressValue.textContent = address || 'N/A';
  }
  if (elements.deleteDescriptionValue) {
    elements.deleteDescriptionValue.textContent = description || 'None';
  }
  toggleButtonLoading(
    elements.confirmDeleteBtn,
    elements.deleteSpinner,
    elements.deleteSubmitLabel,
    false,
    'Delete',
    'Deleting...'
  );

  elements.deleteModal.classList.remove('hidden');
  setTimeout(() => {
    if (elements.confirmDeleteBtn) {
      elements.confirmDeleteBtn.focus();
    }
  }, 0);
}

function closeDeleteModal() {
  if (!elements.deleteModal) {
    return;
  }
  elements.deleteModal.classList.add('hidden');
  state.deleteTarget = null;
  toggleButtonLoading(
    elements.confirmDeleteBtn,
    elements.deleteSpinner,
    elements.deleteSubmitLabel,
    false,
    'Delete',
    'Deleting...'
  );
}

async function submitDelete() {
  if (!state.deleteTarget) {
    return;
  }

  try {
    toggleButtonLoading(
      elements.confirmDeleteBtn,
      elements.deleteSpinner,
      elements.deleteSubmitLabel,
      true,
      'Delete',
      'Deleting...',
    );

    const result = await requestJson(`/interfaces/delete/${encodeURIComponent(state.deleteTarget)}`, {
      method: 'POST',
    });

    if (result.status === 'ok') {
      closeDeleteModal();
      window.location.reload();
      return;
    }

    alert(result.message || 'Failed to delete interface.');
  } catch (error) {
    console.error('Error deleting interface:', error);
    alert('Error deleting interface.');
  } finally {
    toggleButtonLoading(
      elements.confirmDeleteBtn,
      elements.deleteSpinner,
      elements.deleteSubmitLabel,
      false,
      'Delete',
      'Deleting...',
    );
  }
}

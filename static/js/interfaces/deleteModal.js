import { elements, state } from './domCache.js';
import { requestJson, toggleButtonLoading } from './utils.js';

export function bindDeleteModal() {
  if (!elements.deleteModal) {
    return;
  }

  document.querySelectorAll('.delete-btn').forEach((btn) => {
    btn.addEventListener('click', () => openDeleteModal(btn));
  });

  if (elements.cancelDeleteBtn) {
    elements.cancelDeleteBtn.addEventListener('click', () => {
      elements.deleteModal.classList.add('hidden');
      state.deleteTarget = null;
    });
  }

  if (elements.confirmDeleteBtn) {
    elements.confirmDeleteBtn.addEventListener('click', submitDelete);
  }
}

function openDeleteModal(btn) {
  state.deleteTarget = btn.dataset.iface;
  if (elements.deleteIfaceName) {
    elements.deleteIfaceName.textContent = state.deleteTarget || '--';
  }
  elements.deleteModal.classList.remove('hidden');
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

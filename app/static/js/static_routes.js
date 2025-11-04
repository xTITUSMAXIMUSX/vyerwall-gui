/**
 * Static Routes Management JavaScript
 */

// Modal elements
const addRouteModal = document.getElementById('addRouteModal');
const editRouteModal = document.getElementById('editRouteModal');
const deleteRouteModal = document.getElementById('deleteRouteModal');

// Forms
const addRouteForm = document.getElementById('addRouteForm');
const editRouteForm = document.getElementById('editRouteForm');

// State
let currentDeleteRoute = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  bindEventListeners();
});

/**
 * Bind all event listeners
 */
function bindEventListeners() {
  // Add route button
  document.getElementById('addRouteBtn').addEventListener('click', openAddRouteModal);

  // Close modal buttons
  document.getElementById('closeAddRouteModal').addEventListener('click', closeAddRouteModal);
  document.getElementById('cancelAddRoute').addEventListener('click', closeAddRouteModal);
  document.getElementById('closeEditRouteModal').addEventListener('click', closeEditRouteModal);
  document.getElementById('cancelEditRoute').addEventListener('click', closeEditRouteModal);
  document.getElementById('closeDeleteRouteModal').addEventListener('click', closeDeleteRouteModal);
  document.getElementById('cancelDeleteRoute').addEventListener('click', closeDeleteRouteModal);

  // Form submissions
  addRouteForm.addEventListener('submit', handleAddRoute);
  editRouteForm.addEventListener('submit', handleEditRoute);
  document.getElementById('confirmDeleteRoute').addEventListener('click', handleDeleteRoute);

  // Table action buttons
  document.addEventListener('click', (e) => {
    if (e.target.closest('.edit-route-btn')) {
      const btn = e.target.closest('.edit-route-btn');
      openEditRouteModal(btn);
    } else if (e.target.closest('.delete-route-btn')) {
      const btn = e.target.closest('.delete-route-btn');
      openDeleteRouteModal(btn);
    }
  });

  // Close modals on backdrop click
  [addRouteModal, editRouteModal, deleteRouteModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeAllModals();
      }
    });
  });
}

/**
 * Open add route modal
 */
function openAddRouteModal() {
  addRouteForm.reset();
  addRouteModal.classList.remove('hidden');
}

/**
 * Close add route modal
 */
function closeAddRouteModal() {
  addRouteModal.classList.add('hidden');
  addRouteForm.reset();
}

/**
 * Open edit route modal
 */
function openEditRouteModal(button) {
  const destination = button.dataset.destination;
  const nextHop = button.dataset.nextHop;
  const description = button.dataset.description || '';

  document.getElementById('editOldDestination').value = destination;
  document.getElementById('editOldNextHop').value = nextHop;
  document.getElementById('editDestination').value = destination;
  document.getElementById('editNextHop').value = nextHop;
  document.getElementById('editDescription').value = description;

  editRouteModal.classList.remove('hidden');
}

/**
 * Close edit route modal
 */
function closeEditRouteModal() {
  editRouteModal.classList.add('hidden');
  editRouteForm.reset();
}

/**
 * Open delete route modal
 */
function openDeleteRouteModal(button) {
  const destination = button.dataset.destination;
  const nextHop = button.dataset.nextHop;

  currentDeleteRoute = { destination, next_hop: nextHop };

  document.getElementById('deleteDestinationValue').textContent = destination;
  document.getElementById('deleteNextHopValue').textContent = nextHop;

  deleteRouteModal.classList.remove('hidden');
}

/**
 * Close delete route modal
 */
function closeDeleteRouteModal() {
  deleteRouteModal.classList.add('hidden');
  currentDeleteRoute = null;
}

/**
 * Close all modals
 */
function closeAllModals() {
  closeAddRouteModal();
  closeEditRouteModal();
  closeDeleteRouteModal();
}

/**
 * Handle add route form submission
 */
async function handleAddRoute(e) {
  e.preventDefault();

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const spinner = document.getElementById('addRouteSpinner');
  const label = document.getElementById('addRouteLabel');

  // Show loading state
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
  spinner.classList.remove('hidden');
  label.textContent = 'Creating...';

  try {
    const formData = new FormData(addRouteForm);
    const data = {
      destination: formData.get('destination').trim(),
      next_hop: formData.get('next_hop').trim(),
      description: formData.get('description').trim()
    };

    const response = await fetch('/static-routes/api/routes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.status === 'ok') {
      // Update config dirty banner
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Refresh table
      refreshRoutesTable(result.routes);

      // Show success toast
      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('Static route created successfully', 'success');
      }

      // Close modal
      closeAddRouteModal();
    } else {
      throw new Error(result.message || 'Failed to create static route');
    }
  } catch (error) {
    console.error('Error creating route:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to create static route', 'error');
    }
  } finally {
    // Reset loading state
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    spinner.classList.add('hidden');
    label.textContent = 'Create Route';
  }
}

/**
 * Handle edit route form submission
 */
async function handleEditRoute(e) {
  e.preventDefault();

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const spinner = document.getElementById('editRouteSpinner');
  const label = document.getElementById('editRouteLabel');

  // Show loading state
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
  spinner.classList.remove('hidden');
  label.textContent = 'Saving...';

  try {
    const formData = new FormData(editRouteForm);
    const data = {
      old_destination: formData.get('old_destination'),
      old_next_hop: formData.get('old_next_hop'),
      destination: formData.get('destination').trim(),
      next_hop: formData.get('next_hop').trim(),
      description: formData.get('description').trim()
    };

    const response = await fetch('/static-routes/api/routes', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.status === 'ok') {
      // Update config dirty banner
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Refresh table
      refreshRoutesTable(result.routes);

      // Show success toast
      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('Static route updated successfully', 'success');
      }

      // Close modal
      closeEditRouteModal();
    } else {
      throw new Error(result.message || 'Failed to update static route');
    }
  } catch (error) {
    console.error('Error updating route:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to update static route', 'error');
    }
  } finally {
    // Reset loading state
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    spinner.classList.add('hidden');
    label.textContent = 'Save Changes';
  }
}

/**
 * Handle delete route
 */
async function handleDeleteRoute() {
  if (!currentDeleteRoute) return;

  const submitBtn = document.getElementById('confirmDeleteRoute');
  const spinner = document.getElementById('deleteRouteSpinner');
  const label = document.getElementById('deleteRouteLabel');

  // Show loading state
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
  spinner.classList.remove('hidden');
  label.textContent = 'Deleting...';

  try {
    const response = await fetch('/static-routes/api/routes', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentDeleteRoute)
    });

    const result = await response.json();

    if (result.status === 'ok') {
      // Update config dirty banner
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Refresh table
      refreshRoutesTable(result.routes);

      // Show success toast
      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('Static route deleted successfully', 'success');
      }

      // Close modal
      closeDeleteRouteModal();
    } else {
      throw new Error(result.message || 'Failed to delete static route');
    }
  } catch (error) {
    console.error('Error deleting route:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to delete static route', 'error');
    }
  } finally {
    // Reset loading state
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    spinner.classList.add('hidden');
    label.textContent = 'Delete Route';
  }
}

/**
 * Refresh routes table with new data
 */
function refreshRoutesTable(routes) {
  const tbody = document.getElementById('routesTableBody');
  const routeCount = document.getElementById('routeCount');

  // Update count
  routeCount.textContent = `${routes.length} routes`;

  // Clear existing rows
  tbody.innerHTML = '';

  if (routes.length === 0) {
    // Show empty state
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="px-5 py-12 text-center text-gray-400">
          <div class="flex flex-col items-center gap-3">
            <div class="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-2xl flex items-center justify-center">
              <span class="material-icons text-3xl text-gray-600">route</span>
            </div>
            <div>
              <p class="font-semibold text-gray-300 mb-1">No static routes configured</p>
              <p class="text-sm text-gray-500">Click "Add Route" to create your first static route</p>
            </div>
          </div>
        </td>
      </tr>
    `;
  } else {
    // Add route rows
    routes.forEach(route => {
      const row = document.createElement('tr');
      row.className = 'hover:bg-gradient-to-r hover:from-emerald-900/10 hover:to-teal-900/10 transition-all';
      row.innerHTML = `
        <td class="px-5 py-4 font-semibold">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 rounded-lg flex items-center justify-center">
              <span class="material-icons text-emerald-400 text-base">public</span>
            </div>
            <span class="text-white font-mono">${route.destination}</span>
          </div>
        </td>
        <td class="px-5 py-4">
          <span class="font-mono text-cyan-300">${route.next_hop}</span>
        </td>
        <td class="px-5 py-4">
          ${route.description ?
            `<span class="text-gray-300">${route.description}</span>` :
            '<span class="text-gray-500 italic">No description</span>'
          }
        </td>
        <td class="px-5 py-4">
          <div class="flex justify-end gap-3">
            <button
              class="text-blue-400 hover:text-blue-300 transition-colors edit-route-btn p-1"
              data-destination="${route.destination}"
              data-next-hop="${route.next_hop}"
              data-description="${route.description || ''}"
              title="Edit Route"
            >
              <span class="material-icons text-base">edit</span>
            </button>
            <button
              class="text-red-400 hover:text-red-300 transition-colors delete-route-btn p-1"
              data-destination="${route.destination}"
              data-next-hop="${route.next_hop}"
              title="Delete Route"
            >
              <span class="material-icons text-base">delete</span>
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(row);
    });
  }
}

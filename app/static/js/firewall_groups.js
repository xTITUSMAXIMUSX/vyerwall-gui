/**
 * Firewall Groups Management JavaScript
 */

let currentGroupType = null;
let isEditMode = false;

/**
 * Switch between group type tabs
 */
function switchGroupType(groupType) {
  currentGroupType = groupType;

  // Save current tab to localStorage
  localStorage.setItem('firewall_groups_active_tab', groupType);

  // Update tab styles
  document.querySelectorAll('.group-type-tab').forEach(tab => {
    if (tab.dataset.type === groupType) {
      tab.classList.add('bg-purple-500/10', 'text-purple-400', 'border-b-2', 'border-purple-500');
      tab.classList.remove('text-gray-400', 'hover:text-gray-300', 'hover:bg-gray-700/50');
    } else {
      tab.classList.remove('bg-purple-500/10', 'text-purple-400', 'border-b-2', 'border-purple-500');
      tab.classList.add('text-gray-400', 'hover:text-gray-300', 'hover:bg-gray-700/50');
    }
  });

  // Update content visibility
  document.querySelectorAll('.group-type-content').forEach(content => {
    if (content.id === `tab-${groupType}`) {
      content.classList.remove('hidden');
    } else {
      content.classList.add('hidden');
    }
  });
}

/**
 * Open modal to create a new group
 */
function openCreateGroupModal(preselectedType = null) {
  isEditMode = false;
  document.getElementById('isEditing').value = 'false';
  document.getElementById('originalName').value = '';
  document.getElementById('groupForm').reset();

  // Clear members and add one input
  document.getElementById('membersContainer').innerHTML = `
    <div class="flex gap-2 member-input-row">
      <input type="text" class="member-input flex-1 bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500" placeholder="Enter member value">
      <button type="button" onclick="removeMember(this)" class="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors">
        <span class="material-icons">delete</span>
      </button>
    </div>
  `;

  // Show type selection
  document.getElementById('typeSelectionContainer').classList.remove('hidden');

  // Set preselected type if provided
  if (preselectedType) {
    document.getElementById('groupType').value = preselectedType;
    updateGroupTypeUI();
  }

  // Update modal title
  document.getElementById('modalTitle').textContent = 'Create Firewall Group';
  document.getElementById('modalSubtitle').textContent = 'Add a new firewall object group';
  document.getElementById('modalIcon').textContent = 'add';
  document.getElementById('saveGroupBtnText').textContent = 'Create Group';

  document.getElementById('groupModal').classList.remove('hidden');
}

/**
 * Open modal to edit an existing group
 */
function editGroup(group) {
  isEditMode = true;
  document.getElementById('isEditing').value = 'true';
  document.getElementById('originalName').value = group.name;

  // Hide type selection when editing
  document.getElementById('typeSelectionContainer').classList.add('hidden');

  // Set form values
  document.getElementById('groupType').value = group.type;
  document.getElementById('groupName').value = group.name;
  document.getElementById('groupDescription').value = group.description || '';

  // Set members
  document.getElementById('membersContainer').innerHTML = '';
  group.members.forEach(member => {
    addMemberInput(member);
  });

  updateGroupTypeUI();

  // Update modal title
  document.getElementById('modalTitle').textContent = 'Edit Firewall Group';
  document.getElementById('modalSubtitle').textContent = `Modify ${group.name}`;
  document.getElementById('modalIcon').textContent = 'edit';
  document.getElementById('saveGroupBtnText').textContent = 'Update Group';

  document.getElementById('groupModal').classList.remove('hidden');
}

/**
 * Close the group modal
 */
function closeGroupModal() {
  document.getElementById('groupModal').classList.add('hidden');
  document.getElementById('groupForm').reset();
}

/**
 * Update UI based on selected group type
 */
function updateGroupTypeUI() {
  const groupType = document.getElementById('groupType').value;

  if (!groupType || !window.GROUP_TYPES[groupType]) {
    return;
  }

  const config = window.GROUP_TYPES[groupType];
  const membersContainer = document.getElementById('membersContainer');
  const addMemberBtn = membersContainer.nextElementSibling;

  // Update member label and placeholder
  document.getElementById('memberLabel').textContent = config.member_label;
  document.getElementById('memberHint').textContent = config.description;

  // Update placeholder for all member inputs
  document.querySelectorAll('.member-input').forEach(input => {
    input.placeholder = config.placeholder;
  });

  // Disable member management for dynamic-group
  if (groupType === 'dynamic-group') {
    // Disable all member inputs and remove buttons
    document.querySelectorAll('.member-input').forEach(input => {
      input.disabled = true;
      input.classList.add('opacity-50', 'cursor-not-allowed');
    });
    document.querySelectorAll('.member-input-row button').forEach(btn => {
      btn.disabled = true;
      btn.classList.add('opacity-50', 'cursor-not-allowed');
    });
    // Hide the "Add another member" button
    if (addMemberBtn) {
      addMemberBtn.classList.add('hidden');
    }
    // Update hint text
    document.getElementById('memberHint').textContent = 'Members are automatically populated by firewall rules. Manual editing is not allowed.';
  } else {
    // Enable member inputs for other types
    document.querySelectorAll('.member-input').forEach(input => {
      input.disabled = false;
      input.classList.remove('opacity-50', 'cursor-not-allowed');
    });
    document.querySelectorAll('.member-input-row button').forEach(btn => {
      btn.disabled = false;
      btn.classList.remove('opacity-50', 'cursor-not-allowed');
    });
    // Show the "Add another member" button
    if (addMemberBtn) {
      addMemberBtn.classList.remove('hidden');
    }
  }
}

/**
 * Add a new member input field
 */
function addMemberInput(value = '') {
  const groupType = document.getElementById('groupType').value;
  const config = window.GROUP_TYPES[groupType] || {};
  const placeholder = config.placeholder || 'Enter member value';

  const container = document.getElementById('membersContainer');
  const row = document.createElement('div');
  row.className = 'flex gap-2 member-input-row';
  row.innerHTML = `
    <input type="text" class="member-input flex-1 bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500" placeholder="${placeholder}" value="${value}">
    <button type="button" onclick="removeMember(this)" class="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors">
      <span class="material-icons">delete</span>
    </button>
  `;
  container.appendChild(row);
}

/**
 * Remove a member input field
 */
function removeMember(button) {
  const container = document.getElementById('membersContainer');
  const rows = container.querySelectorAll('.member-input-row');

  // Keep at least one input
  if (rows.length > 1) {
    button.closest('.member-input-row').remove();
  } else {
    // Clear the last input instead of removing it
    container.querySelector('.member-input').value = '';
  }
}

/**
 * Save group (create or update)
 */
async function saveGroup() {
  const saveBtn = document.getElementById('saveGroupBtn');
  const saveBtnText = document.getElementById('saveGroupBtnText');
  const spinner = document.getElementById('saveGroupSpinner');
  const icon = document.getElementById('saveGroupIcon');
  const originalText = saveBtnText.textContent;
  const isEditing = document.getElementById('isEditing').value === 'true';
  const originalName = document.getElementById('originalName').value;

  // Show loading state
  saveBtn.disabled = true;
  saveBtn.classList.add('opacity-70', 'cursor-not-allowed');
  saveBtnText.textContent = isEditing ? 'Updating...' : 'Creating...';
  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');

  try {
    const groupType = document.getElementById('groupType').value;
    const groupName = document.getElementById('groupName').value.trim();
    const description = document.getElementById('groupDescription').value.trim();

    // Collect members
    const memberInputs = document.querySelectorAll('.member-input');
    const members = Array.from(memberInputs)
      .map(input => input.value.trim())
      .filter(value => value !== '');

    // Validation
    if (!groupType) {
      throw new Error('Please select a group type');
    }

    if (!groupName) {
      throw new Error('Please enter a group name');
    }

    if (members.length === 0) {
      throw new Error('Please add at least one member');
    }

    const data = {
      type: groupType,
      name: groupName,
      description: description,
      members: members
    };

    let response;
    if (isEditing) {
      // Update existing group
      response = await fetch(`/firewall/groups/api/groups/${groupType}/${encodeURIComponent(originalName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } else {
      // Create new group
      response = await fetch('/firewall/groups/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    }

    const result = await response.json();

    if (result.status === 'ok') {
      // Update config dirty banner if available
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Show success toast
      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast(
          result.message || (isEditing ? 'Group updated successfully' : 'Group created successfully'),
          'success'
        );
      }

      closeGroupModal();

      // Save current tab before reloading
      localStorage.setItem('firewall_groups_active_tab', groupType);

      // Reload page to show updated groups
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } else {
      throw new Error(result.message || 'Failed to save group');
    }
  } catch (error) {
    console.error('Error saving group:', error);

    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message, 'error');
    } else {
      alert('Error: ' + error.message);
    }
  } finally {
    // Reset loading state
    saveBtn.disabled = false;
    saveBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    saveBtnText.textContent = originalText;
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
  }
}

/**
 * Delete a group
 */
async function deleteGroup(groupType, groupName) {
  if (!confirm(`Are you sure you want to delete the firewall group "${groupName}"?\n\nThis action cannot be undone.`)) {
    return;
  }

  try {
    const response = await fetch(`/firewall/groups/api/groups/${groupType}/${encodeURIComponent(groupName)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();

    if (result.status === 'ok') {
      // Update config dirty banner
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Show success toast
      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast(
          result.message || 'Group deleted successfully',
          'success'
        );
      }

      // Save current tab before reloading
      localStorage.setItem('firewall_groups_active_tab', groupType);

      // Reload page to show updated groups
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } else {
      throw new Error(result.message || 'Failed to delete group');
    }
  } catch (error) {
    console.error('Error deleting group:', error);

    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message, 'error');
    } else {
      alert('Error: ' + error.message);
    }
  }
}

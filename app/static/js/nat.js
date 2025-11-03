// NAT Page JavaScript

// State
let isEditingSource = false;
let isEditingDest = false;
let dragState = { index: null, type: null };

// Order staging state - these store full rule objects, not just numbers
let sourceOriginalOrder = [];
let sourcePendingOrder = [];
let sourceOrderDirty = false;
let destOriginalOrder = [];
let destPendingOrder = [];
let destOrderDirty = false;

// ===== SOURCE NAT MODAL FUNCTIONS =====

function openSourceNATModal() {
  isEditingSource = false;
  document.getElementById('sourceEditRuleNumber').value = '';
  document.getElementById('sourceNATForm').reset();
  document.getElementById('sourceModalTitle').textContent = 'Add Source NAT Rule';
  document.getElementById('sourceNATModal').classList.remove('hidden');
}

function closeSourceNATModal() {
  document.getElementById('sourceNATModal').classList.add('hidden');
  document.getElementById('sourceNATForm').reset();
  isEditingSource = false;
}

function editSourceNATRule(rule) {
  isEditingSource = true;
  document.getElementById('sourceEditRuleNumber').value = rule.rule_number;
  document.getElementById('sourceModalTitle').textContent = `Edit Source NAT Rule #${rule.rule_number}`;

  document.getElementById('source_description').value = rule.description || '';
  document.getElementById('source_outbound_interface').value = rule.outbound_interface || '';
  document.getElementById('source_source_address').value = rule.source_address || '';
  document.getElementById('source_translation').value = rule.translation || 'masquerade';

  document.getElementById('sourceNATModal').classList.remove('hidden');
}

async function saveSourceNATRule() {
  const saveBtn = document.getElementById('saveSourceNATBtn');
  const saveBtnText = document.getElementById('saveSourceNATBtnText');
  const spinner = document.getElementById('saveSourceNATSpinner');
  const icon = document.getElementById('saveSourceNATIcon');
  const originalText = saveBtnText.textContent;

  // Show loading state
  saveBtn.disabled = true;
  saveBtn.classList.add('opacity-70', 'cursor-not-allowed');
  saveBtnText.textContent = 'Saving...';
  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');

  try {
    const data = {
      type: 'source',
      description: document.getElementById('source_description').value,
      outbound_interface: document.getElementById('source_outbound_interface').value,
      source_address: document.getElementById('source_source_address').value,
      translation: document.getElementById('source_translation').value
    };

    // Validation
    if (!data.outbound_interface || !data.source_address) {
      throw new Error('Please fill in all required fields');
    }

    let response;
    if (isEditingSource) {
      const ruleNumber = document.getElementById('sourceEditRuleNumber').value;
      response = await fetch(`/api/nat/rule/source/${ruleNumber}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } else {
      response = await fetch('/api/nat/rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    }

    const result = await response.json();

    if (result.status === 'ok') {
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      refreshRulesTable(result.rules);
      closeSourceNATModal();

      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast(
          isEditingSource ? 'Source NAT rule updated successfully' : 'Source NAT rule created successfully',
          'success'
        );
      }
    } else {
      throw new Error(result.message || 'Failed to save NAT rule');
    }
  } catch (error) {
    console.error('Error saving source NAT rule:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to save NAT rule', 'error');
    } else {
      alert(error.message || 'Failed to save NAT rule');
    }
  } finally {
    // Reset button state
    saveBtn.disabled = false;
    saveBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    saveBtnText.textContent = originalText;
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
  }
}

// ===== DESTINATION NAT MODAL FUNCTIONS =====

function openDestinationNATModal() {
  isEditingDest = false;
  document.getElementById('destEditRuleNumber').value = '';
  document.getElementById('destinationNATForm').reset();
  document.getElementById('destModalTitle').textContent = 'Add Destination NAT Rule';
  document.getElementById('destinationNATModal').classList.remove('hidden');
}

function closeDestinationNATModal() {
  document.getElementById('destinationNATModal').classList.add('hidden');
  document.getElementById('destinationNATForm').reset();
  isEditingDest = false;
}

function editDestinationNATRule(rule) {
  isEditingDest = true;
  document.getElementById('destEditRuleNumber').value = rule.rule_number;
  document.getElementById('destModalTitle').textContent = `Edit Destination NAT Rule #${rule.rule_number}`;

  document.getElementById('dest_description').value = rule.description || '';
  document.getElementById('dest_inbound_interface').value = rule.inbound_interface || '';
  document.getElementById('dest_protocol').value = rule.protocol || 'tcp';
  document.getElementById('dest_destination_address').value = rule.destination_address || '';
  document.getElementById('dest_destination_port').value = rule.destination_port || '';
  document.getElementById('dest_translation_address').value = rule.translation_address || '';
  document.getElementById('dest_translation_port').value = rule.translation_port || '';

  document.getElementById('destinationNATModal').classList.remove('hidden');
}

async function saveDestinationNATRule() {
  const saveBtn = document.getElementById('saveDestNATBtn');
  const saveBtnText = document.getElementById('saveDestNATBtnText');
  const spinner = document.getElementById('saveDestNATSpinner');
  const icon = document.getElementById('saveDestNATIcon');
  const originalText = saveBtnText.textContent;

  // Show loading state
  saveBtn.disabled = true;
  saveBtn.classList.add('opacity-70', 'cursor-not-allowed');
  saveBtnText.textContent = 'Saving...';
  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');

  try {
    const data = {
      type: 'destination',
      description: document.getElementById('dest_description').value,
      inbound_interface: document.getElementById('dest_inbound_interface').value,
      protocol: document.getElementById('dest_protocol').value,
      destination_address: document.getElementById('dest_destination_address').value,
      destination_port: document.getElementById('dest_destination_port').value,
      translation_address: document.getElementById('dest_translation_address').value,
      translation_port: document.getElementById('dest_translation_port').value
    };

    // Validation
    if (!data.inbound_interface || !data.destination_port || !data.translation_address) {
      throw new Error('Please fill in all required fields');
    }

    let response;
    if (isEditingDest) {
      const ruleNumber = document.getElementById('destEditRuleNumber').value;
      response = await fetch(`/api/nat/rule/destination/${ruleNumber}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } else {
      response = await fetch('/api/nat/rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    }

    const result = await response.json();

    if (result.status === 'ok') {
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      refreshRulesTable(result.rules);
      closeDestinationNATModal();

      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast(
          isEditingDest ? 'Destination NAT rule updated successfully' : 'Destination NAT rule created successfully',
          'success'
        );
      }
    } else {
      throw new Error(result.message || 'Failed to save NAT rule');
    }
  } catch (error) {
    console.error('Error saving destination NAT rule:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to save NAT rule', 'error');
    } else {
      alert(error.message || 'Failed to save NAT rule');
    }
  } finally {
    // Reset button state
    saveBtn.disabled = false;
    saveBtn.classList.remove('opacity-70', 'cursor-not-allowed');
    saveBtnText.textContent = originalText;
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
  }
}

// ===== DELETE FUNCTION =====

// Delete modal state
let pendingDelete = {
  ruleType: null,
  ruleNumber: null
};

function openDeleteNATModal(ruleType, ruleNumber) {
  // Store pending delete info
  pendingDelete.ruleType = ruleType;
  pendingDelete.ruleNumber = ruleNumber;

  // Update modal text
  const typeSpan = document.getElementById('deleteNATType');
  const numberSpan = document.getElementById('deleteNATNumber');

  if (typeSpan) {
    typeSpan.textContent = ruleType;
  }
  if (numberSpan) {
    numberSpan.textContent = `#${ruleNumber}`;
  }

  // Show modal
  const modal = document.getElementById('deleteNATModal');
  if (modal) {
    modal.classList.remove('hidden');
  }
}

function closeDeleteNATModal() {
  // Clear pending delete
  pendingDelete.ruleType = null;
  pendingDelete.ruleNumber = null;

  // Hide modal
  const modal = document.getElementById('deleteNATModal');
  if (modal) {
    modal.classList.add('hidden');
  }

  // Reset UI
  const spinner = document.getElementById('deleteNATSpinner');
  const icon = document.getElementById('deleteNATIcon');
  const label = document.getElementById('deleteNATSubmitLabel');
  const btn = document.getElementById('confirmDeleteNAT');

  if (spinner) spinner.classList.add('hidden');
  if (icon) icon.classList.remove('hidden');
  if (label) label.textContent = 'Delete';
  if (btn) btn.disabled = false;
}

async function confirmDeleteNATRule() {
  if (!pendingDelete.ruleType || !pendingDelete.ruleNumber) {
    return;
  }

  const { ruleType, ruleNumber } = pendingDelete;

  // Show loading state
  const spinner = document.getElementById('deleteNATSpinner');
  const icon = document.getElementById('deleteNATIcon');
  const label = document.getElementById('deleteNATSubmitLabel');
  const btn = document.getElementById('confirmDeleteNAT');

  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');
  if (label) label.textContent = 'Deleting...';
  if (btn) btn.disabled = true;

  try {
    const response = await fetch(`/api/nat/rule/${ruleType}/${ruleNumber}`, {
      method: 'DELETE'
    });

    const result = await response.json();

    if (result.status === 'ok') {
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      refreshRulesTable(result.rules);

      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('NAT rule deleted successfully', 'success');
      }

      // Close modal
      closeDeleteNATModal();
    } else {
      throw new Error(result.message || 'Failed to delete NAT rule');
    }
  } catch (error) {
    console.error('Error deleting rule:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to delete NAT rule', 'error');
    } else {
      alert(error.message || 'Failed to delete NAT rule');
    }

    // Reset UI on error
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
    if (label) label.textContent = 'Delete';
    if (btn) btn.disabled = false;
  }
}

// Keep the old deleteRule function for backwards compatibility, but now it opens the modal
async function deleteRule(ruleType, ruleNumber) {
  openDeleteNATModal(ruleType, ruleNumber);
}

// ===== DRAG AND DROP FUNCTIONS =====

function clearDropTargets() {
  document.querySelectorAll('.nat-drop-target').forEach(el => {
    el.classList.remove('nat-drop-target');
  });
}

function markDropTarget(row) {
  clearDropTargets();
  row.classList.add('nat-drop-target');
}

// Track if drag handlers are already initialized to prevent duplicates
let dragHandlersInitialized = false;

function initializeDragAndDrop() {
  console.log('Initializing drag and drop, already initialized:', dragHandlersInitialized);

  // Always re-initialize when called (after table re-render)
  dragHandlersInitialized = false;

  // Initialize drag and drop for source NAT table
  const sourceRows = document.querySelectorAll('#sourceNATTable tr[draggable="true"]');
  console.log('Found source rows:', sourceRows.length);

  sourceRows.forEach((row, index) => {
    row.addEventListener('dragstart', (event) => {
      if (event.target.closest('button')) {
        event.preventDefault();
        return;
      }
      dragState.index = parseInt(row.dataset.index);
      dragState.type = 'source';
      row.classList.add('opacity-50');
      event.dataTransfer.effectAllowed = 'move';
    });

    row.addEventListener('dragend', () => {
      row.classList.remove('opacity-50');
      clearDropTargets();
      dragState.index = null;
      dragState.type = null;
    });

    row.addEventListener('dragover', (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      markDropTarget(row);
    });

    row.addEventListener('drop', (event) => {
      event.preventDefault();
      if (dragState.index === null || dragState.type !== 'source') {
        clearDropTargets();
        return;
      }

      const targetIndex = parseInt(row.dataset.index);
      console.log('Source drop: fromIndex=', dragState.index, 'toIndex=', targetIndex);
      if (isNaN(targetIndex) || targetIndex === dragState.index) {
        clearDropTargets();
        return;
      }

      handleReorder('source', dragState.index, targetIndex);
      clearDropTargets();
    });

    row.addEventListener('dragleave', (event) => {
      if (!row.contains(event.relatedTarget)) {
        row.classList.remove('nat-drop-target');
      }
    });
  });

  // Initialize drag and drop for destination NAT table
  const destRows = document.querySelectorAll('#destinationNATTable tr[draggable="true"]');
  destRows.forEach((row, index) => {
    row.addEventListener('dragstart', (event) => {
      if (event.target.closest('button')) {
        event.preventDefault();
        return;
      }
      dragState.index = parseInt(row.dataset.index);
      dragState.type = 'destination';
      row.classList.add('opacity-50');
      event.dataTransfer.effectAllowed = 'move';
    });

    row.addEventListener('dragend', () => {
      row.classList.remove('opacity-50');
      clearDropTargets();
      dragState.index = null;
      dragState.type = null;
    });

    row.addEventListener('dragover', (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      markDropTarget(row);
    });

    row.addEventListener('drop', (event) => {
      event.preventDefault();
      if (dragState.index === null || dragState.type !== 'destination') {
        clearDropTargets();
        return;
      }

      const targetIndex = parseInt(row.dataset.index);
      if (isNaN(targetIndex) || targetIndex === dragState.index) {
        clearDropTargets();
        return;
      }

      handleReorder('destination', dragState.index, targetIndex);
      clearDropTargets();
    });

    row.addEventListener('dragleave', (event) => {
      if (!row.contains(event.relatedTarget)) {
        row.classList.remove('nat-drop-target');
      }
    });
  });
}

function handleReorder(ruleType, fromIndex, toIndex) {
  console.log(`handleReorder called: type=${ruleType}, from=${fromIndex}, to=${toIndex}`);

  // Stage the reorder instead of applying immediately
  if (ruleType === 'source') {
    console.log('Before reorder, sourcePendingOrder length:', sourcePendingOrder.length);
    console.log('Before reorder, sourcePendingOrder:', sourcePendingOrder.map(r => r.rule_number));

    // If not dirty yet, save original order
    if (!sourceOrderDirty) {
      sourceOriginalOrder = [...sourcePendingOrder];
      console.log('Saved original order');
    }

    // Reorder the pending array (array of rule objects)
    const [movedRule] = sourcePendingOrder.splice(fromIndex, 1);
    sourcePendingOrder.splice(toIndex, 0, movedRule);

    console.log('After reorder, sourcePendingOrder:', sourcePendingOrder.map(r => r.rule_number));

    // Mark as dirty
    sourceOrderDirty = true;

    // Show order controls
    document.getElementById('sourceOrderControls').classList.remove('hidden');

    // Disable add button
    const addBtn = document.getElementById('addSourceNATBtn');
    if (addBtn) {
      addBtn.disabled = true;
      addBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    console.log('About to render table with pending order');
    // Re-render table with pending order
    renderTableWithPendingOrder('source');

  } else { // destination
    // If not dirty yet, save original order
    if (!destOrderDirty) {
      destOriginalOrder = [...destPendingOrder];
    }

    // Reorder the pending array (array of rule objects)
    const [movedRule] = destPendingOrder.splice(fromIndex, 1);
    destPendingOrder.splice(toIndex, 0, movedRule);

    // Mark as dirty
    destOrderDirty = true;

    // Show order controls
    document.getElementById('destOrderControls').classList.remove('hidden');

    // Disable add button
    const addBtn = document.getElementById('addDestNATBtn');
    if (addBtn) {
      addBtn.disabled = true;
      addBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    // Re-render table with pending order
    renderTableWithPendingOrder('destination');
  }
}

function renderTableWithPendingOrder(ruleType) {
  console.log(`renderTableWithPendingOrder called for type: ${ruleType}`);

  // Re-render the entire table with the pending order (like firewall does)
  const tbody = document.getElementById(ruleType === 'source' ? 'sourceNATTable' : 'destinationNATTable');

  if (!tbody) {
    console.error('Table body not found for type:', ruleType);
    return;
  }

  // Get the pending order for this rule type
  const pendingRules = ruleType === 'source' ? sourcePendingOrder : destPendingOrder;

  console.log('Pending rules to render:', pendingRules.length);
  console.log('Pending rules:', pendingRules.map((r, i) => `[${i}] #${r.rule_number}`));

  if (!pendingRules || pendingRules.length === 0) {
    console.warn('No pending rules to render for type:', ruleType);
    return;
  }

  // Completely re-render the table with the new order
  if (ruleType === 'source') {
    const newHTML = pendingRules.map((rule, index) => `
      <tr class="hover:bg-gray-700/30 transition-colors cursor-grab" draggable="true" data-rule-number="${rule.rule_number}" data-rule-type="source" data-index="${index}">
        <td class="px-4 py-3">
          <span class="material-icons text-gray-500 text-base">drag_indicator</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-lg flex items-center justify-center">
              <span class="text-sm font-bold text-teal-400">${100 + index}</span>
            </div>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm text-gray-300">${rule.description || 'No description'}</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-1">
            <span class="material-icons text-xs text-cyan-400">settings_ethernet</span>
            <span class="text-sm font-mono text-cyan-300">${rule.outbound_interface || 'N/A'}</span>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-gray-300">${rule.source_address || 'N/A'}</span>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-green-300">${rule.translation || 'N/A'}</span>
        </td>
        <td class="px-4 py-3 text-right">
          <div class="flex items-center justify-end gap-2">
            <button onclick='editSourceNATRule(${JSON.stringify(rule)})' class="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-500/10 rounded-lg" title="Edit">
              <span class="material-icons text-sm">edit</span>
            </button>
            <button onclick="deleteRule('${rule.type}', '${rule.rule_number}')" class="text-red-400 hover:text-red-300 transition-colors p-2 hover:bg-red-500/10 rounded-lg" title="Delete">
              <span class="material-icons text-sm">delete</span>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
    console.log('Generated new HTML for', pendingRules.length, 'source rules');
    tbody.innerHTML = newHTML;
  } else { // destination
    tbody.innerHTML = pendingRules.map((rule, index) => `
      <tr class="hover:bg-gray-700/30 transition-colors cursor-grab" draggable="true" data-rule-number="${rule.rule_number}" data-rule-type="destination" data-index="${index}">
        <td class="px-4 py-3">
          <span class="material-icons text-gray-500 text-base">drag_indicator</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg flex items-center justify-center">
              <span class="text-sm font-bold text-blue-400">${100 + index}</span>
            </div>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm text-gray-300">${rule.description || 'No description'}</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-1">
            <span class="material-icons text-xs text-blue-400">settings_ethernet</span>
            <span class="text-sm font-mono text-blue-300">${rule.inbound_interface || 'N/A'}</span>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-gray-300">${rule.protocol || 'N/A'}</span>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-gray-300">${rule.destination_address || 'N/A'}</span>${rule.destination_port ? '<span class="text-sm font-bold text-purple-400">:</span><span class="text-sm font-semibold text-purple-300">' + rule.destination_port + '</span>' : ''}
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-green-300">${rule.translation_address || 'N/A'}</span>${rule.translation_port ? '<span class="text-sm font-bold text-cyan-400">:</span><span class="text-sm font-semibold text-cyan-300">' + rule.translation_port + '</span>' : ''}
        </td>
        <td class="px-4 py-3 text-right">
          <div class="flex items-center justify-end gap-2">
            <button onclick='editDestinationNATRule(${JSON.stringify(rule)})' class="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-500/10 rounded-lg" title="Edit">
              <span class="material-icons text-sm">edit</span>
            </button>
            <button onclick="deleteRule('${rule.type}', '${rule.rule_number}')" class="text-red-400 hover:text-red-300 transition-colors p-2 hover:bg-red-500/10 rounded-lg" title="Delete">
              <span class="material-icons text-sm">delete</span>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  console.log('Table rendered, re-initializing drag and drop');

  // Re-initialize drag and drop
  initializeDragAndDrop();

  console.log('Render complete');
}

// ===== ORDER CONTROL FUNCTIONS =====

async function saveSourceOrder() {
  if (!sourceOrderDirty) return;

  // Toggle loading state
  const saveBtn = document.getElementById('saveSourceOrderBtn');
  const spinner = document.getElementById('saveSourceOrderSpinner');
  const icon = document.getElementById('saveSourceOrderIcon');
  const label = document.getElementById('saveSourceOrderLabel');

  if (saveBtn && spinner && icon && label) {
    saveBtn.disabled = true;
    saveBtn.classList.add('opacity-70', 'cursor-not-allowed');
    spinner.classList.remove('hidden');
    icon.classList.add('hidden');
    label.textContent = 'Saving...';
  }

  try {
    // Send the full rule objects in the new order, not just numbers
    // This ensures the backend has all the data it needs
    const ruleData = sourcePendingOrder.map(rule => ({
      rule_number: rule.rule_number,
      description: rule.description,
      outbound_interface: rule.outbound_interface,
      source_address: rule.source_address,
      translation: rule.translation
    }));

    console.log('Saving source order with', ruleData.length, 'rules');
    console.log('First rule:', ruleData[0]);

    const response = await fetch('/api/nat/reorder/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules: ruleData })
    });

    const result = await response.json();

    if (result.status === 'ok') {
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Reset dirty state
      sourceOrderDirty = false;
      sourceOriginalOrder = [];

      // Hide order controls
      document.getElementById('sourceOrderControls').classList.add('hidden');

      // Enable add button
      const addBtn = document.getElementById('addSourceNATBtn');
      if (addBtn) {
        addBtn.disabled = false;
        addBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }

      // Refresh table with new data from backend
      refreshRulesTable(result.rules);

      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('Source NAT rules reordered successfully', 'success');
      }
    } else {
      throw new Error(result.message || 'Failed to reorder source NAT rules');
    }
  } catch (error) {
    console.error('Error saving source NAT order:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to reorder source NAT rules', 'error');
    }
  } finally {
    // Reset loading state
    const saveBtn = document.getElementById('saveSourceOrderBtn');
    const spinner = document.getElementById('saveSourceOrderSpinner');
    const icon = document.getElementById('saveSourceOrderIcon');
    const label = document.getElementById('saveSourceOrderLabel');

    if (saveBtn && spinner && icon && label) {
      saveBtn.disabled = false;
      saveBtn.classList.remove('opacity-70', 'cursor-not-allowed');
      spinner.classList.add('hidden');
      icon.classList.remove('hidden');
      label.textContent = 'Save Order';
    }
  }
}

function discardSourceOrder() {
  if (!sourceOrderDirty) return;

  // Restore original order
  sourcePendingOrder = [...sourceOriginalOrder];

  // Reset dirty state
  sourceOrderDirty = false;
  sourceOriginalOrder = [];

  // Hide order controls
  document.getElementById('sourceOrderControls').classList.add('hidden');

  // Enable add button
  const addBtn = document.getElementById('addSourceNATBtn');
  if (addBtn) {
    addBtn.disabled = false;
    addBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  // Re-render table with original order
  renderTableWithPendingOrder('source');

  if (window.ConfigManager && window.ConfigManager.showToast) {
    window.ConfigManager.showToast('Source NAT order changes discarded', 'info');
  }
}

async function saveDestOrder() {
  if (!destOrderDirty) return;

  // Toggle loading state
  const saveBtn = document.getElementById('saveDestOrderBtn');
  const spinner = document.getElementById('saveDestOrderSpinner');
  const icon = document.getElementById('saveDestOrderIcon');
  const label = document.getElementById('saveDestOrderLabel');

  if (saveBtn && spinner && icon && label) {
    saveBtn.disabled = true;
    saveBtn.classList.add('opacity-70', 'cursor-not-allowed');
    spinner.classList.remove('hidden');
    icon.classList.add('hidden');
    label.textContent = 'Saving...';
  }

  try {
    // Send the full rule objects in the new order, not just numbers
    // This ensures the backend has all the data it needs
    const ruleData = destPendingOrder.map(rule => ({
      rule_number: rule.rule_number,
      description: rule.description,
      inbound_interface: rule.inbound_interface,
      destination_address: rule.destination_address,
      destination_port: rule.destination_port,
      protocol: rule.protocol,
      translation_address: rule.translation_address,
      translation_port: rule.translation_port
    }));

    console.log('Saving destination order with', ruleData.length, 'rules');
    console.log('First rule:', ruleData[0]);

    const response = await fetch('/api/nat/reorder/destination', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules: ruleData })
    });

    const result = await response.json();

    if (result.status === 'ok') {
      if (result.config_dirty && window.ConfigManager && window.ConfigManager.updateBanner) {
        window.ConfigManager.updateBanner(true);
      }

      // Reset dirty state
      destOrderDirty = false;
      destOriginalOrder = [];

      // Hide order controls
      document.getElementById('destOrderControls').classList.add('hidden');

      // Enable add button
      const addBtn = document.getElementById('addDestNATBtn');
      if (addBtn) {
        addBtn.disabled = false;
        addBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      }

      // Refresh table with new data from backend
      refreshRulesTable(result.rules);

      if (window.ConfigManager && window.ConfigManager.showToast) {
        window.ConfigManager.showToast('Destination NAT rules reordered successfully', 'success');
      }
    } else {
      throw new Error(result.message || 'Failed to reorder destination NAT rules');
    }
  } catch (error) {
    console.error('Error saving destination NAT order:', error);
    if (window.ConfigManager && window.ConfigManager.showToast) {
      window.ConfigManager.showToast(error.message || 'Failed to reorder destination NAT rules', 'error');
    }
  } finally {
    // Reset loading state
    const saveBtn = document.getElementById('saveDestOrderBtn');
    const spinner = document.getElementById('saveDestOrderSpinner');
    const icon = document.getElementById('saveDestOrderIcon');
    const label = document.getElementById('saveDestOrderLabel');

    if (saveBtn && spinner && icon && label) {
      saveBtn.disabled = false;
      saveBtn.classList.remove('opacity-70', 'cursor-not-allowed');
      spinner.classList.add('hidden');
      icon.classList.remove('hidden');
      label.textContent = 'Save Order';
    }
  }
}

function discardDestOrder() {
  if (!destOrderDirty) return;

  // Restore original order
  destPendingOrder = [...destOriginalOrder];

  // Reset dirty state
  destOrderDirty = false;
  destOriginalOrder = [];

  // Hide order controls
  document.getElementById('destOrderControls').classList.add('hidden');

  // Enable add button
  const addBtn = document.getElementById('addDestNATBtn');
  if (addBtn) {
    addBtn.disabled = false;
    addBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  // Re-render table with original order
  renderTableWithPendingOrder('destination');

  if (window.ConfigManager && window.ConfigManager.showToast) {
    window.ConfigManager.showToast('Destination NAT order changes discarded', 'info');
  }
}

// ===== REFRESH TABLES FUNCTION =====

function refreshRulesTable(rules) {
  const sourceTable = document.getElementById('sourceNATTable');
  const destTable = document.getElementById('destinationNATTable');

  if (!rules || rules.length === 0) {
    sourceTable.innerHTML = `
      <tr>
        <td colspan="7" class="px-4 py-8 text-center">
          <div class="flex flex-col items-center gap-3">
            <div class="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-full flex items-center justify-center">
              <span class="material-icons text-3xl text-gray-500">call_made</span>
            </div>
            <p class="text-gray-400">No source NAT rules configured</p>
            <p class="text-sm text-gray-500">Click "Add Source NAT" to create your first rule</p>
          </div>
        </td>
      </tr>
    `;
    destTable.innerHTML = `
      <tr>
        <td colspan="8" class="px-4 py-8 text-center">
          <div class="flex flex-col items-center gap-3">
            <div class="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-full flex items-center justify-center">
              <span class="material-icons text-3xl text-gray-500">call_received</span>
            </div>
            <p class="text-gray-400">No destination NAT rules configured</p>
            <p class="text-sm text-gray-500">Click "Add Destination NAT" to create your first port forwarding rule</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  // Separate rules by type
  const sourceRules = rules.filter(rule => rule.type === 'source');
  const destinationRules = rules.filter(rule => rule.type === 'destination');

  // Initialize pending order arrays with full rule objects if not dirty
  if (!sourceOrderDirty) {
    sourcePendingOrder = [...sourceRules];
  }
  if (!destOrderDirty) {
    destPendingOrder = [...destinationRules];
  }

  // Render source NAT rules
  if (sourceRules.length === 0) {
    sourceTable.innerHTML = `
      <tr>
        <td colspan="7" class="px-4 py-8 text-center">
          <div class="flex flex-col items-center gap-3">
            <div class="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-full flex items-center justify-center">
              <span class="material-icons text-3xl text-gray-500">call_made</span>
            </div>
            <p class="text-gray-400">No source NAT rules configured</p>
            <p class="text-sm text-gray-500">Click "Add Source NAT" to create your first rule</p>
          </div>
        </td>
      </tr>
    `;
  } else {
    sourceTable.innerHTML = sourceRules.map((rule, index) => `
      <tr class="hover:bg-gray-700/30 transition-colors cursor-grab" draggable="true" data-rule-number="${rule.rule_number}" data-rule-type="source" data-index="${index}">
        <td class="px-4 py-3">
          <span class="material-icons text-gray-500 text-base">drag_indicator</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-lg flex items-center justify-center">
              <span class="text-sm font-bold text-teal-400">${rule.rule_number}</span>
            </div>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm text-gray-300">${rule.description || 'No description'}</span>
        </td>
        <td class="px-4 py-3">
          <div class="flex items-center gap-1">
            <span class="material-icons text-xs text-cyan-400">settings_ethernet</span>
            <span class="text-sm font-mono text-cyan-300">${rule.outbound_interface || 'N/A'}</span>
          </div>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-gray-300">${rule.source_address || 'N/A'}</span>
        </td>
        <td class="px-4 py-3">
          <span class="text-sm font-mono text-green-300">${rule.translation || 'N/A'}</span>
        </td>
        <td class="px-4 py-3 text-right">
          <div class="flex items-center justify-end gap-2">
            <button onclick='editSourceNATRule(${JSON.stringify(rule)})' class="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-500/10 rounded-lg" title="Edit">
              <span class="material-icons text-sm">edit</span>
            </button>
            <button onclick="deleteRule('${rule.type}', '${rule.rule_number}')" class="text-red-400 hover:text-red-300 transition-colors p-2 hover:bg-red-500/10 rounded-lg" title="Delete">
              <span class="material-icons text-sm">delete</span>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  // Render destination NAT rules
  if (destinationRules.length === 0) {
    destTable.innerHTML = `
      <tr>
        <td colspan="8" class="px-4 py-8 text-center">
          <div class="flex flex-col items-center gap-3">
            <div class="w-16 h-16 bg-gradient-to-br from-gray-700 to-gray-800 rounded-full flex items-center justify-center">
              <span class="material-icons text-3xl text-gray-500">call_received</span>
            </div>
            <p class="text-gray-400">No destination NAT rules configured</p>
            <p class="text-sm text-gray-500">Click "Add Destination NAT" to create your first port forwarding rule</p>
          </div>
        </td>
      </tr>
    `;
  } else {
    destTable.innerHTML = destinationRules.map((rule, index) => {
      const translationDisplay = rule.translation_address === 'redirect'
        ? '<span class="text-sm font-mono text-green-300">Redirect</span>'
        : `<span class="text-sm font-mono text-green-300">${rule.translation_address || 'N/A'}</span>`;

      return `
        <tr class="hover:bg-gray-700/30 transition-colors cursor-grab" draggable="true" data-rule-number="${rule.rule_number}" data-rule-type="destination" data-index="${index}">
          <td class="px-4 py-3">
            <span class="material-icons text-gray-500 text-base">drag_indicator</span>
          </td>
          <td class="px-4 py-3">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg flex items-center justify-center">
                <span class="text-sm font-bold text-blue-400">${rule.rule_number}</span>
              </div>
            </div>
          </td>
          <td class="px-4 py-3">
            <span class="text-sm text-gray-300">${rule.description || 'No description'}</span>
          </td>
          <td class="px-4 py-3">
            <div class="flex items-center gap-1">
              <span class="material-icons text-xs text-cyan-400">settings_ethernet</span>
              <span class="text-sm font-mono text-cyan-300">${rule.inbound_interface || 'N/A'}</span>
            </div>
          </td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-1 bg-purple-500/20 border border-purple-500/30 text-purple-300 rounded-lg text-xs font-medium uppercase">
              ${rule.protocol || 'N/A'}
            </span>
          </td>
          <td class="px-4 py-3">
            <span class="text-sm font-mono text-gray-300">${rule.destination_address || 'Any'}</span>${rule.destination_port ? `<span class="text-sm font-bold text-purple-400">:</span><span class="text-sm font-semibold text-purple-300">${rule.destination_port}</span>` : ''}
          </td>
          <td class="px-4 py-3">
            ${translationDisplay}${rule.translation_port ? `<span class="text-sm font-bold text-cyan-400">:</span><span class="text-sm font-semibold text-cyan-300">${rule.translation_port}</span>` : ''}
          </td>
          <td class="px-4 py-3 text-right">
            <div class="flex items-center justify-end gap-2">
              <button onclick='editDestinationNATRule(${JSON.stringify(rule)})' class="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-500/10 rounded-lg" title="Edit">
                <span class="material-icons text-sm">edit</span>
              </button>
              <button onclick="deleteRule('${rule.type}', '${rule.rule_number}')" class="text-red-400 hover:text-red-300 transition-colors p-2 hover:bg-red-500/10 rounded-lg" title="Delete">
                <span class="material-icons text-sm">delete</span>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Re-initialize drag and drop after rendering
  initializeDragAndDrop();
}

// ===== INITIALIZE ON PAGE LOAD =====

document.addEventListener('DOMContentLoaded', () => {
  // Initialize pending order arrays from server-side data
  if (window.initialNATRules) {
    const sourceRules = window.initialNATRules.filter(rule => rule.type === 'source');
    const destRules = window.initialNATRules.filter(rule => rule.type === 'destination');

    sourcePendingOrder = [...sourceRules];
    destPendingOrder = [...destRules];

    console.log('Initialized sourcePendingOrder with', sourcePendingOrder.length, 'rules');
    console.log('Initialized destPendingOrder with', destPendingOrder.length, 'rules');
  }

  initializeDragAndDrop();
});

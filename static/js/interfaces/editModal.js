import { elements } from './domCache.js';
import {
  isValidIpv4Cidr,
  requestJson,
  syncAddressFieldWithMode,
  syncNatSelectWithMode,
  toggleButtonLoading,
} from './utils.js';

export function bindEditModal() {
  if (!elements.editForm || !elements.editModal) {
    return;
  }

  document.querySelectorAll('.edit-btn').forEach((btn) => {
    btn.addEventListener('click', () => openEditModal(btn));
  });

  if (elements.editModeSelect) {
    elements.editModeSelect.addEventListener('change', () => {
      syncAddressFieldWithMode(elements.editModeSelect, elements.editAddressInput);
      syncNatSelectWithMode(elements.editModeSelect, elements.editNatSelect);
    });
  }

  if (elements.cancelEditBtn) {
    elements.cancelEditBtn.addEventListener('click', () => {
      elements.editModal.classList.add('hidden');
    });
  }

  elements.editForm.addEventListener('submit', submitEditForm);
}

function openEditModal(btn) {
  const iface = btn.dataset.iface;
  const description = btn.dataset.description;
  const address = btn.dataset.address;
  const mode = btn.dataset.mode || (address === 'dhcp' ? 'dhcp' : 'static');
  const natInterface = btn.dataset.natInterface || '';
  const natRuleNumber = btn.dataset.natRule || '';
  const zone = btn.dataset.zone || '';

  if (elements.editIfaceInput) {
    elements.editIfaceInput.value = iface;
  }
  if (elements.editDescriptionInput) {
    elements.editDescriptionInput.value = description;
  }
  if (elements.editNatRuleInput) {
    elements.editNatRuleInput.value = natRuleNumber;
  }
  if (elements.editModeSelect) {
    elements.editModeSelect.value = mode;
  }
  if (elements.editAddressInput) {
    elements.editAddressInput.value = address;
    syncAddressFieldWithMode(elements.editModeSelect, elements.editAddressInput);
  }
  if (elements.editNatSelect) {
    elements.editNatSelect.value = natInterface;
    syncNatSelectWithMode(elements.editModeSelect, elements.editNatSelect);
  }
  if (elements.editZoneSelect) {
    elements.editZoneSelect.value = zone;
  }

  elements.editModal.classList.remove('hidden');
}

async function submitEditForm(event) {
  event.preventDefault();

  const iface = elements.editIfaceInput ? elements.editIfaceInput.value : '';
  const description = elements.editDescriptionInput ? elements.editDescriptionInput.value : '';
  const mode = elements.editModeSelect ? elements.editModeSelect.value : 'static';
  const addressFieldValue = elements.editAddressInput ? elements.editAddressInput.value.trim() : '';
  const natInterfaceValue = elements.editNatSelect ? elements.editNatSelect.value : '';
  const natRuleNumberValue = elements.editNatRuleInput ? elements.editNatRuleInput.value : '';
  const zoneValue = elements.editZoneSelect ? elements.editZoneSelect.value : '';
  let payloadAddress = addressFieldValue;

  if (mode === 'dhcp') {
    payloadAddress = 'dhcp';
  } else if (!payloadAddress) {
    alert('Please provide a CIDR address for static mode.');
    return;
  } else if (!isValidIpv4Cidr(payloadAddress)) {
    alert('Address must be a valid IPv4 CIDR (e.g. 192.168.9.1/24).');
    return;
  }

  try {
    toggleButtonLoading(
      elements.editSubmitBtn,
      elements.editSpinner,
      elements.editSubmitLabel,
      true,
      'Save',
      'Saving...',
    );

    const result = await requestJson(`/interfaces/edit/${encodeURIComponent(iface)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description,
        mode,
        address: payloadAddress,
        source_nat_interface: natInterfaceValue,
        nat_rule_number: natRuleNumberValue,
        zone: zoneValue,
      }),
    });

    if (result.status !== 'ok') {
      alert(result.message || 'Failed to update interface.');
      return;
    }

    elements.editModal.classList.add('hidden');
    window.location.reload();
  } catch (error) {
    console.error('Error updating interface:', error);
    alert('Error updating interface.');
  } finally {
    toggleButtonLoading(
      elements.editSubmitBtn,
      elements.editSpinner,
      elements.editSubmitLabel,
      false,
      'Save',
      'Saving...',
    );
  }
}

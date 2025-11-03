import { elements } from './domCache.js';
import {
  isValidIpv4Cidr,
  requestJson,
  syncAddressFieldWithMode,
  syncNatSelectWithMode,
  toggleButtonLoading,
  showValidationError,
} from './utils.js';

export function bindCreateVlanModal() {
  if (!elements.createForm || !elements.createModal) {
    return;
  }

  if (elements.createVlanBtn) {
    elements.createVlanBtn.addEventListener('click', () => {
      elements.createModal.classList.remove('hidden');
      syncNatSelectWithMode(elements.vlanModeSelect, elements.vlanNatSelect);
    });
  }

  if (elements.cancelCreateBtn) {
    elements.cancelCreateBtn.addEventListener('click', () => {
      elements.createModal.classList.add('hidden');
    });
  }

  if (elements.createCloseBtn) {
    elements.createCloseBtn.addEventListener('click', () => {
      elements.createModal.classList.add('hidden');
    });
  }

  if (elements.vlanModeSelect && elements.vlanAddressInput) {
    syncAddressFieldWithMode(elements.vlanModeSelect, elements.vlanAddressInput);
    syncNatSelectWithMode(elements.vlanModeSelect, elements.vlanNatSelect);
    elements.vlanModeSelect.addEventListener('change', () => {
      syncAddressFieldWithMode(elements.vlanModeSelect, elements.vlanAddressInput);
      syncNatSelectWithMode(elements.vlanModeSelect, elements.vlanNatSelect);
    });
  }

  elements.createForm.addEventListener('submit', submitCreateVlanForm);
}

async function submitCreateVlanForm(event) {
  event.preventDefault();

  const parentInterface = (elements.vlanParentSelect?.value || '').trim();
  const vlanId = (document.querySelector('#vlanId')?.value || '').trim();
  const description = (document.querySelector('#vlanDescription')?.value || '').trim();
  const mode = elements.vlanModeSelect ? elements.vlanModeSelect.value : 'dhcp';
  const addressValue = elements.vlanAddressInput ? elements.vlanAddressInput.value.trim() : '';
  const natInterfaceValue = elements.vlanNatSelect ? elements.vlanNatSelect.value : '';
  const zoneValue = elements.vlanZoneSelect ? elements.vlanZoneSelect.value : '';
  let payloadAddress = addressValue;

  if (!parentInterface) {
    alert('Select a parent interface.');
    return;
  }
  if (!vlanId) {
    alert('Provide a VLAN ID.');
    return;
  }

  if (mode === 'dhcp') {
    payloadAddress = 'dhcp';
  } else if (!payloadAddress) {
    alert('VLAN requires an address in static mode.');
    return;
  } else if (!isValidIpv4Cidr(payloadAddress)) {
    alert('Address must be a valid IPv4 CIDR (e.g. 192.168.9.1/24).');
    return;
  }

  try {
    toggleButtonLoading(
      elements.createVlanSubmitBtn,
      elements.createVlanSpinner,
      elements.createVlanSubmitLabel,
      true,
      'Create',
      'Creating...',
    );

    const result = await requestJson('/interfaces/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        parent: parentInterface,
        vlan_id: vlanId,
        description,
        mode,
        address: payloadAddress,
        source_nat_interface: natInterfaceValue,
        zone: zoneValue,
      }),
    });

    if (result.status === 'ok') {
      window.location.reload();
      return;
    }

    showValidationError(result.message || 'Failed to create VLAN interface.');
  } catch (error) {
    console.error('Error creating VLAN:', error);
    alert('Error creating VLAN interface.');
  } finally {
    toggleButtonLoading(
      elements.createVlanSubmitBtn,
      elements.createVlanSpinner,
      elements.createVlanSubmitLabel,
      false,
      'Create',
      'Creating...',
    );
  }
}

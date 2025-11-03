import { elements } from './domCache.js';
import {
  isValidIpv4Cidr,
  requestJson,
  syncAddressFieldWithMode,
  syncNatSelectWithMode,
  toggleButtonLoading,
  showValidationError,
} from './utils.js';

export function bindAddInterfaceModal() {
  if (!elements.addInterfaceForm || !elements.addInterfaceModal) {
    return;
  }

  if (elements.addInterfaceBtn) {
    elements.addInterfaceBtn.addEventListener('click', () => {
      elements.addInterfaceModal.classList.remove('hidden');
      syncNatSelectWithMode(elements.addInterfaceModeSelect, elements.addInterfaceNatSelect);
    });
  }

  if (elements.cancelAddInterfaceBtn) {
    elements.cancelAddInterfaceBtn.addEventListener('click', () => {
      elements.addInterfaceModal.classList.add('hidden');
    });
  }

  if (elements.addInterfaceCloseBtn) {
    elements.addInterfaceCloseBtn.addEventListener('click', () => {
      elements.addInterfaceModal.classList.add('hidden');
    });
  }

  if (elements.addInterfaceModeSelect && elements.addInterfaceAddressInput) {
    syncAddressFieldWithMode(elements.addInterfaceModeSelect, elements.addInterfaceAddressInput);
    syncNatSelectWithMode(elements.addInterfaceModeSelect, elements.addInterfaceNatSelect);
    elements.addInterfaceModeSelect.addEventListener('change', () => {
      syncAddressFieldWithMode(elements.addInterfaceModeSelect, elements.addInterfaceAddressInput);
      syncNatSelectWithMode(elements.addInterfaceModeSelect, elements.addInterfaceNatSelect);
    });
  }

  elements.addInterfaceForm.addEventListener('submit', submitAddInterfaceForm);
}

async function submitAddInterfaceForm(event) {
  event.preventDefault();

  const ifaceSelect = document.querySelector('#addInterfaceSelect');
  const iface = ifaceSelect ? ifaceSelect.value.trim() : '';
  const description = (document.querySelector('#addInterfaceDescription')?.value || '').trim();
  const mode = elements.addInterfaceModeSelect ? elements.addInterfaceModeSelect.value : 'static';
  const addressValue = elements.addInterfaceAddressInput ? elements.addInterfaceAddressInput.value.trim() : '';
  const natInterfaceValue = elements.addInterfaceNatSelect ? elements.addInterfaceNatSelect.value : '';
  const zoneValue = elements.addInterfaceZoneSelect ? elements.addInterfaceZoneSelect.value : '';
  let payloadAddress = addressValue;

  if (!iface) {
    alert('Please choose an interface to configure.');
    return;
  }

  if (mode === 'dhcp') {
    payloadAddress = 'dhcp';
  } else {
    if (!payloadAddress) {
      alert('Please enter an address for static mode.');
      return;
    }
    if (!isValidIpv4Cidr(payloadAddress)) {
      alert('Address must be a valid IPv4 CIDR (e.g. 192.168.9.1/24).');
      return;
    }
  }

  try {
    toggleButtonLoading(
      elements.addInterfaceSubmitBtn,
      elements.addInterfaceSpinner,
      elements.addInterfaceSubmitLabel,
      true,
      'Create',
      'Creating...',
    );

    const result = await requestJson('/interfaces/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interface: iface,
        description,
        address: payloadAddress,
        mode,
        source_nat_interface: natInterfaceValue,
        zone: zoneValue,
      }),
    });

    if (result.status === 'ok') {
      window.location.reload();
      return;
    }

    showValidationError(result.message || 'Failed to add interface.');
  } catch (error) {
    console.error('Error adding interface:', error);
    alert('Error adding interface.');
  } finally {
    toggleButtonLoading(
      elements.addInterfaceSubmitBtn,
      elements.addInterfaceSpinner,
      elements.addInterfaceSubmitLabel,
      false,
      'Create',
      'Creating...',
    );
  }
}

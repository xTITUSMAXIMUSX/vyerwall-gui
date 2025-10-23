const IPV4_CIDR_REGEX = /^(?:\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;

export function isValidIpv4Cidr(address) {
  if (!address) {
    return false;
  }
  if (!IPV4_CIDR_REGEX.test(address)) {
    return false;
  }
  const [ipPart, prefixPart] = address.split('/');
  const octets = ipPart.split('.').map(Number);
  const prefix = Number(prefixPart);
  const octetsValid = octets.every((octet) => octet >= 0 && octet <= 255);
  return octetsValid && prefix >= 0 && prefix <= 32;
}

export async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.message || `Request failed with status ${response.status}`;
    return { status: 'error', message };
  }
  return payload;
}

export function toggleButtonLoading(buttonEl, spinnerEl, labelEl, isLoading, idleText, busyText) {
  if (!buttonEl || !spinnerEl || !labelEl) {
    return;
  }
  if (isLoading) {
    buttonEl.disabled = true;
    buttonEl.classList.add('opacity-70', 'cursor-not-allowed', 'animate-pulse');
    spinnerEl.classList.remove('hidden');
    labelEl.textContent = busyText;
  } else {
    buttonEl.disabled = false;
    buttonEl.classList.remove('opacity-70', 'cursor-not-allowed', 'animate-pulse');
    spinnerEl.classList.add('hidden');
    labelEl.textContent = idleText;
  }
}

export function syncAddressFieldWithMode(modeSelect, addressInput) {
  if (!modeSelect || !addressInput) {
    return;
  }

  if (!addressInput.dataset.cidrPattern) {
    addressInput.dataset.cidrPattern = addressInput.getAttribute('pattern') || '';
  }

  if (modeSelect.value === 'dhcp') {
    addressInput.value = 'dhcp';
    addressInput.readOnly = true;
    addressInput.classList.add('cursor-not-allowed', 'opacity-70');
    addressInput.removeAttribute('pattern');
  } else {
    if (addressInput.value === 'dhcp') {
      addressInput.value = '';
    }
    addressInput.readOnly = false;
    addressInput.classList.remove('cursor-not-allowed', 'opacity-70');
    if (addressInput.dataset.cidrPattern) {
      addressInput.setAttribute('pattern', addressInput.dataset.cidrPattern);
    }
  }
}

export function syncNatSelectWithMode(modeSelect, natSelect) {
  if (!modeSelect || !natSelect) {
    return;
  }
  const shouldDisable = modeSelect.value === 'dhcp';
  natSelect.disabled = shouldDisable;
  if (shouldDisable) {
    natSelect.value = '';
    natSelect.classList.add('cursor-not-allowed', 'opacity-70');
  } else {
    natSelect.classList.remove('cursor-not-allowed', 'opacity-70');
  }
}

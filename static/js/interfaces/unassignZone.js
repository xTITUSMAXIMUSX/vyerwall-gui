import { requestJson } from './utils.js';

export function bindUnassignZoneButtons() {
  document.querySelectorAll('.unassign-zone-btn').forEach((btn) => {
    btn.addEventListener('click', () => handleUnassign(btn));
  });
}

async function handleUnassign(btn) {
  const iface = btn.dataset.iface;
  const zone = btn.dataset.zone;
  if (!iface) {
    return;
  }
  if (!zone) {
    alert('This interface is not assigned to a zone.');
    return;
  }
  if (!window.confirm(`Remove ${iface} from zone ${zone}?`)) {
    return;
  }

  const mode = (btn.dataset.mode || '').toLowerCase();
  let address = btn.dataset.address || '';
  let payloadMode = mode;
  if (mode === 'dhcp') {
    address = 'dhcp';
  }
  if (payloadMode !== 'dhcp' && payloadMode !== 'static') {
    payloadMode = address === 'dhcp' ? 'dhcp' : 'static';
  }
  if (payloadMode === 'static' && (!address || address === 'dhcp')) {
    alert('This interface must have a valid address before removing zone membership.');
    return;
  }

  const payload = {
    description: btn.dataset.description || '',
    mode: payloadMode,
    address,
    source_nat_interface: btn.dataset.natInterface || '',
    nat_rule_number: btn.dataset.natRule || '',
    zone: '',
  };

  btn.classList.add('opacity-60', 'cursor-not-allowed');
  btn.style.pointerEvents = 'none';

  try {
    const result = await requestJson(`/interfaces/edit/${encodeURIComponent(iface)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (result.status !== 'ok') {
      alert(result.message || 'Failed to unassign interface from zone.');
      btn.classList.remove('opacity-60', 'cursor-not-allowed');
      btn.style.pointerEvents = '';
      return;
    }

    const row = btn.closest('tr');
    if (row) {
      const zoneBadge = row.querySelector('.iface-zone');
      if (zoneBadge) {
        zoneBadge.textContent = 'Zone: Unassigned';
      }
      const editBtn = row.querySelector('.edit-btn');
      if (editBtn) {
        editBtn.dataset.zone = '';
      }
    }
    btn.remove();
  } catch (error) {
    console.error('Error unassigning zone:', error);
    alert('Error removing interface from zone.');
    btn.classList.remove('opacity-60', 'cursor-not-allowed');
    btn.style.pointerEvents = '';
  }
}

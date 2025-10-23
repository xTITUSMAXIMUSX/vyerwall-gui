import { requestJson } from './utils.js';

export function bindPowerControls() {
  document.querySelectorAll('.power-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const iface = btn.dataset.iface;
      const isActive = btn.dataset.state === 'UP';
      const endpoint = isActive ? `/interfaces/disable/${iface}` : `/interfaces/enable/${iface}`;

      try {
        const result = await requestJson(endpoint, { method: 'POST' });
        if (result.status !== 'ok') {
          alert(result.message || 'Failed to change interface state.');
          return;
        }
        const row = btn.closest('tr');
        if (!row) {
          return;
        }
        const statusCell = row.querySelector('.iface-status');
        const icon = statusCell ? statusCell.querySelector('.material-icons') : null;
        if (!icon) {
          return;
        }
        if (isActive) {
          icon.classList.remove('text-green-500');
          icon.classList.add('text-red-500');
          icon.nextSibling.textContent = ' Down';
          btn.dataset.state = 'DOWN';
        } else {
          icon.classList.remove('text-red-500');
          icon.classList.add('text-green-500');
          icon.nextSibling.textContent = ' Active';
          btn.dataset.state = 'UP';
        }
      } catch (error) {
        console.error('Error toggling interface:', error);
        alert('Failed to change interface state.');
      }
    });
  });
}

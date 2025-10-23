import { cacheElements } from './domCache.js';
import { bindAddInterfaceModal } from './addInterfaceModal.js';
import { bindCreateVlanModal } from './vlanModal.js';
import { bindDeleteModal } from './deleteModal.js';
import { bindEditModal } from './editModal.js';
import { bindPowerControls } from './powerControls.js';
import { bindUnassignZoneButtons } from './unassignZone.js';

function initInterfacesPage() {
  cacheElements();
  bindPowerControls();
  bindEditModal();
  bindUnassignZoneButtons();
  bindAddInterfaceModal();
  bindCreateVlanModal();
  bindDeleteModal();
}

document.addEventListener('DOMContentLoaded', initInterfacesPage);

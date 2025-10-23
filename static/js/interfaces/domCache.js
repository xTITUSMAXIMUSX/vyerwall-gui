export const elements = {};

export const state = {
  deleteTarget: null,
};

export function cacheElements() {
  elements.addInterfaceBtn = document.querySelector('#addInterfaceBtn');
  elements.addInterfaceModal = document.querySelector('#addInterfaceModal');
  elements.addInterfaceForm = document.querySelector('#addInterfaceForm');
  elements.addInterfaceModeSelect = document.querySelector('#addInterfaceMode');
  elements.addInterfaceAddressInput = document.querySelector('#addInterfaceAddress');
  elements.addInterfaceNatSelect = document.querySelector('#addInterfaceNat');
  elements.addInterfaceZoneSelect = document.querySelector('#addInterfaceZone');
  elements.addInterfaceSubmitBtn = document.querySelector('#submitAddInterface');
  elements.addInterfaceSpinner = document.querySelector('#addInterfaceSpinner');
  elements.addInterfaceSubmitLabel = document.querySelector('#addInterfaceSubmitLabel');
  elements.cancelAddInterfaceBtn = document.querySelector('#cancelAddInterface');

  elements.createVlanBtn = document.querySelector('#createVlanBtn');
  elements.createModal = document.querySelector('#createModal');
  elements.createForm = document.querySelector('#createForm');
  elements.vlanModeSelect = document.querySelector('#vlanMode');
  elements.vlanAddressInput = document.querySelector('#vlanAddress');
  elements.vlanNatSelect = document.querySelector('#vlanNatInterface');
  elements.vlanZoneSelect = document.querySelector('#vlanZone');
  elements.createVlanSubmitBtn = document.querySelector('#createVlanSubmit');
  elements.createVlanSpinner = document.querySelector('#createVlanSpinner');
  elements.createVlanSubmitLabel = document.querySelector('#createVlanSubmitLabel');
  elements.cancelCreateBtn = document.querySelector('#cancelCreate');

  elements.editModal = document.querySelector('#editModal');
  elements.editForm = document.querySelector('#editForm');
  elements.editModeSelect = document.querySelector('#editMode');
  elements.editAddressInput = document.querySelector('#editAddress');
  elements.editNatSelect = document.querySelector('#editNatInterface');
  elements.editNatRuleInput = document.querySelector('#editNatRuleNumber');
  elements.editSubmitBtn = elements.editForm ? elements.editForm.querySelector('button[type="submit"]') : null;
  elements.editSpinner = document.querySelector('#editSpinner');
  elements.editSubmitLabel = document.querySelector('#editSubmitLabel');
  elements.editZoneSelect = document.querySelector('#editZone');
  elements.cancelEditBtn = document.querySelector('#cancelEdit');
  elements.editDescriptionInput = document.querySelector('#editDescription');
  elements.editIfaceInput = document.querySelector('#editIface');

  elements.deleteModal = document.querySelector('#deleteModal');
  elements.deleteIfaceName = document.querySelector('#deleteIfaceName');
  elements.cancelDeleteBtn = document.querySelector('#cancelDelete');
  elements.confirmDeleteBtn = document.querySelector('#confirmDelete');
  elements.deleteSpinner = document.querySelector('#deleteSpinner');
  elements.deleteSubmitLabel = document.querySelector('#deleteSubmitLabel');
}

(function initFirewallState(root) {
  const namespace = root.Vyerwall || (root.Vyerwall = {});
  const firewallNs = namespace.Firewall || (namespace.Firewall = {});
  const constants = firewallNs.constants;

  const data = {
    names: [],
    metadata: {},
    zoneGroups: {},
    zoneList: [],
    interfaces: {
      unassigned: [],
    },
    selectedName: null,
    selectedZone: null,
    isLoading: false,
    rules: [],
    rulesBaseline: [],
    orderDirty: false,
  };

  let modals = {};
  let forms = {};
  let formButtons = {};
  let confirmButtons = {};
  let confirmSpinners = {};
  let infoLabels = {};
  let reorderControls = {};
  let reorderSpinner = null;
  let reorderSaveLabel = null;
  let dragState = { index: null };

  function query(selector) {
    return selector ? document.querySelector(selector) : null;
  }

  function initializeDomReferences() {
    modals = {
      add: document.getElementById('addRuleModal'),
      edit: document.getElementById('editRuleModal'),
      delete: document.getElementById('deleteRuleModal'),
      disable: document.getElementById('disableRuleModal'),
    };

    forms = {
      add: document.getElementById('addRuleForm'),
      edit: document.getElementById('editRuleForm'),
    };

    formButtons = {
      addSubmit: document.getElementById('addRuleSubmit'),
      addSpinner: document.getElementById('addRuleSpinner'),
      addLabel: document.getElementById('addRuleSubmitLabel'),
      editSubmit: document.getElementById('editRuleSubmit'),
      editSpinner: document.getElementById('editRuleSpinner'),
      editLabel: document.getElementById('editRuleSubmitLabel'),
    };

    confirmButtons = {
      delete: document.getElementById('confirmDeleteRule'),
      disable: document.getElementById('confirmDisableRule'),
    };

    confirmSpinners = {
      deleteSpinner: document.getElementById('deleteRuleSpinner'),
      deleteLabel: document.getElementById('deleteRuleSubmitLabel'),
      disableSpinner: document.getElementById('disableRuleSpinner'),
      disableLabel: document.getElementById('disableRuleSubmitLabel'),
    };

    infoLabels = {
      delete: document.getElementById('deleteRuleMessage'),
      disable: document.getElementById('disableRuleMessage'),
    };

    reorderControls = {
      container: query(constants.selectors.reorderControls),
      save: query(constants.selectors.reorderSave),
      cancel: query(constants.selectors.reorderCancel),
    };

    reorderSpinner = document.getElementById('reorderSpinner');
    reorderSaveLabel = document.getElementById('reorderSaveLabel');
    dragState = { index: null };
  }

  firewallNs.state = {
    data,
    get modals() {
      return modals;
    },
    get forms() {
      return forms;
    },
    get formButtons() {
      return formButtons;
    },
    get confirmButtons() {
      return confirmButtons;
    },
    get confirmSpinners() {
      return confirmSpinners;
    },
    get infoLabels() {
      return infoLabels;
    },
    get reorderControls() {
      return reorderControls;
    },
    get reorderSpinner() {
      return reorderSpinner;
    },
    get reorderSaveLabel() {
      return reorderSaveLabel;
    },
    get dragState() {
      return dragState;
    },
    initializeDomReferences,
  };
})(window);

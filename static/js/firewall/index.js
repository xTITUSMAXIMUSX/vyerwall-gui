document.addEventListener('DOMContentLoaded', () => {
  const namespace = window.Vyerwall || {};
  const controller = namespace.Firewall && namespace.Firewall.controller;
  if (controller && typeof controller.init === 'function') {
    controller.init();
  }
});

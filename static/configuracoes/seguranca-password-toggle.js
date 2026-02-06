(function () {
  const FORM_ID = 'security-password-form';
  const TOGGLE_ID = 'toggle-security-passwords';
  const PANEL_ID = 'seguranca-panel-content';
  const PASSWORD_FIELD_NAMES = ['old_password', 'new_password1', 'new_password2'];

  const getScope = (root) => (root && root.querySelector ? root : document);

  const setupPasswordToggle = (root) => {
    const scope = getScope(root);
    const form = scope.querySelector(`#${FORM_ID}`) || document.querySelector(`#${FORM_ID}`);
    if (!form || form.dataset.securityPasswordToggleBound === 'true') {
      return;
    }

    const toggle = form.querySelector(`#${TOGGLE_ID}`);
    if (!toggle) {
      return;
    }

    const passwordInputs = PASSWORD_FIELD_NAMES.map((name) =>
      form.querySelector(`input[name="${name}"]`)
    ).filter(Boolean);

    if (!passwordInputs.length) {
      return;
    }

    const updatePasswordVisibility = () => {
      const nextType = toggle.checked ? 'text' : 'password';
      passwordInputs.forEach((input) => {
        if (input.type !== nextType) {
          input.type = nextType;
        }
      });
    };

    toggle.checked = false;
    updatePasswordVisibility();
    toggle.addEventListener('change', updatePasswordVisibility);
    form.dataset.securityPasswordToggleBound = 'true';
  };

  document.addEventListener('DOMContentLoaded', () => {
    setupPasswordToggle(document);
  });

  document.body.addEventListener('htmx:afterSwap', (event) => {
    const target = event.target;
    if (!target || target.id !== PANEL_ID) {
      return;
    }
    setupPasswordToggle(target);
  });
})();

    (function () {
      const input = document.querySelector('[data-confirm-input]');
      const submit = document.querySelector('[data-confirm-submit]');
      if (!input || !submit) {
        return;
      }
      const expectedToken = (input.getAttribute('data-confirm-token') || '').trim().toUpperCase();
      const updateState = () => {
        const normalized = (input.value || '').trim().toUpperCase();
        if (input.value !== normalized) {
          input.value = normalized;
        }
        const isValid = normalized === expectedToken && expectedToken.length > 0;
        submit.disabled = !isValid;
        submit.setAttribute('aria-disabled', String(!isValid));
      };
      input.addEventListener('input', updateState);
      input.addEventListener('blur', updateState);
      updateState();
      input.focus();
    })();
  

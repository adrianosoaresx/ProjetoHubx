  (function () {
    const modalContainer = document.getElementById('modal');
    if (!modalContainer) {
      return;
    }
    const dialog = modalContainer.querySelector('[data-modal-root]');
    if (!dialog) {
      return;
    }
    const focusableSelectors = [
      'a[href]','area[href]','input:not([disabled])','select:not([disabled])','textarea:not([disabled])',
      'button:not([disabled])','[tabindex]:not([tabindex="-1"])'
    ].join(',');
    const focusableElements = Array.from(dialog.querySelectorAll(focusableSelectors)).filter((el) => !el.hasAttribute('hidden'));
    const previouslyFocused = window.HubxModalTrigger instanceof HTMLElement ? window.HubxModalTrigger : document.activeElement;
    function closeModal(event) {
      if (event) {
        event.preventDefault();
      }
      modalContainer.innerHTML = '';
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus();
      }
      if (window.HubxModalTrigger) {
        window.HubxModalTrigger = null;
      }
    }
    const cancelButtons = dialog.querySelectorAll('[data-modal-dismiss]');
    cancelButtons.forEach((button) => {
      button.addEventListener('click', closeModal);
    });

    const form = dialog.querySelector('form[data-redirect-url]');
    if (form) {
      form.addEventListener('htmx:afterRequest', (event) => {
        if (!event.detail || event.detail.successful === false) {
          return;
        }

        let redirectHeader = null;
        const xhr = event.detail.xhr;
        if (xhr && typeof xhr.getResponseHeader === 'function') {
          redirectHeader = xhr.getResponseHeader('HX-Redirect');
        }

        if (!redirectHeader && event.detail.fetchResponse && event.detail.fetchResponse.headers) {
          const headers = event.detail.fetchResponse.headers;
          if (typeof headers.get === 'function') {
            redirectHeader = headers.get('HX-Redirect');
          }
        }

        const redirectUrl = redirectHeader || form.dataset.redirectUrl;
        if (redirectUrl) {
          window.location.href = redirectUrl;
        }
      });
    }
    modalContainer.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeModal(event);
      }
      if (event.key === 'Tab' && focusableElements.length) {
        const first = focusableElements[0];
        const last = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    });
    if (focusableElements.length) {
      focusableElements[0].focus();
    }
  })();

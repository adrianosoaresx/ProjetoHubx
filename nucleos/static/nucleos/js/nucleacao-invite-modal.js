  (function () {
    const modalContainer = document.getElementById('modal');
    const dialog = modalContainer ? modalContainer.querySelector('[data-modal-root]') : null;

    if (!dialog) {
      return;
    }

    const focusableSelectors = [
      'a[href]','area[href]','input:not([disabled])','select:not([disabled])','textarea:not([disabled])','button:not([disabled])','[tabindex]:not([tabindex="-1"])'
    ].join(',');
    const focusableElements = Array.from(dialog.querySelectorAll(focusableSelectors)).filter((el) => !el.hasAttribute('hidden'));
    const previouslyFocused = window.HubxModalTrigger instanceof HTMLElement ? window.HubxModalTrigger : document.activeElement;

    function closeModal(event) {
      if (event) {
        event.preventDefault();
      }
      if (modalContainer) {
        modalContainer.innerHTML = '';
        if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
          previouslyFocused.focus();
        }
        if (window.HubxModalTrigger) {
          window.HubxModalTrigger = null;
        }
      } else if (history.length > 1) {
        history.back();
      }
    }

    dialog.querySelectorAll('[data-modal-dismiss]').forEach((button) => {
      button.addEventListener('click', closeModal);
    });

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

    const initialFocusElement = dialog.querySelector('[data-initial-focus]');
    if (initialFocusElement && typeof initialFocusElement.focus === 'function') {
      initialFocusElement.focus();
    } else if (focusableElements.length) {
      focusableElements[0].focus();
    }
  })();

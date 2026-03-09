  (function () {
    const modalContainer = document.getElementById('modal');
    if (!modalContainer) return;
    const dialog = modalContainer.querySelector('[data-modal-root]');
    if (!dialog) return;

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

    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) {
        closeModal(event);
      }
    });

    const cancelButtons = dialog.querySelectorAll('[data-modal-dismiss]');
    cancelButtons.forEach((button) => button.addEventListener('click', closeModal));

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

  (function () {
    const dialog = document.querySelector('[data-modal-root]');
    if (!dialog) return;

    const ratingContainers = dialog.querySelectorAll('[data-rating-stars]');
    ratingContainers.forEach((container) => {
      const hiddenInput = container.querySelector('input[type="hidden"][name="score"]');
      const stars = Array.from(container.querySelectorAll('[data-rating-star]'));
      if (!hiddenInput || !stars.length) return;

      let currentValue = parseInt(hiddenInput.value, 10) || 0;

      const applyState = (value) => {
        stars.forEach((star) => {
          const starValue = Number(star.dataset.value);
          const icon = star.querySelector('[data-star-icon]');
          const isActive = value >= starValue;
          star.setAttribute('aria-checked', value === starValue ? 'true' : 'false');
          star.setAttribute('tabindex', starValue === (value || 1) ? '0' : '-1');

          star.classList.toggle('text-[#FFD700]', isActive);
          star.classList.toggle('fill-[#FFD700]', isActive);
          star.classList.toggle('text-[var(--text-muted)]', !isActive);
          if (icon) {
            icon.classList.toggle('text-[#FFD700]', isActive);
            icon.classList.toggle('fill-[#FFD700]', isActive);
            icon.classList.toggle('fill-transparent', !isActive);
          }
        });
      };

      const commitValue = (value) => {
        currentValue = value;
        hiddenInput.value = value;
        applyState(value);
      };

      applyState(currentValue);

      stars.forEach((star) => {
        const starValue = Number(star.dataset.value);

        star.addEventListener('mouseenter', () => applyState(starValue));
        star.addEventListener('mouseleave', () => applyState(currentValue));

        star.addEventListener('click', () => {
          commitValue(starValue);
          star.focus();
        });

        star.addEventListener('keydown', (event) => {
          const keys = ['Enter', ' '];
          if (keys.includes(event.key)) {
            event.preventDefault();
            commitValue(starValue);
            return;
          }

          if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
            event.preventDefault();
            const nextValue = Math.min(5, (currentValue || 0) + 1);
            commitValue(nextValue);
            stars[nextValue - 1]?.focus();
          }

          if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
            event.preventDefault();
            const prevValue = Math.max(1, (currentValue || 1) - 1);
            commitValue(prevValue);
            stars[prevValue - 1]?.focus();
          }
        });
      });

      container.addEventListener('mouseleave', () => applyState(currentValue));
    });
  })();

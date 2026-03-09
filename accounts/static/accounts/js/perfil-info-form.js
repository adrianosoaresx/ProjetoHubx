  (function () {
    const container = document.getElementById('perfil-info-card');
    if (!container) {
      return;
    }
    const accordions = container.querySelectorAll('[data-accordion]');
    accordions.forEach((accordion) => {
      const toggle = accordion.querySelector('[data-accordion-toggle]');
      const panel = accordion.querySelector('[data-accordion-panel]');
      const icon = accordion.querySelector('[data-accordion-icon]');
      if (!(toggle instanceof HTMLElement) || !(panel instanceof HTMLElement)) {
        return;
      }

      const setExpanded = (expanded) => {
        toggle.setAttribute('aria-expanded', String(expanded));
        panel.classList.toggle('hidden', !expanded);
        if (icon instanceof HTMLElement) {
          icon.classList.toggle('rotate-180', expanded);
        }
      };

      const initialExpanded = toggle.getAttribute('aria-expanded') === 'true';
      setExpanded(initialExpanded);

      toggle.addEventListener('click', () => {
        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        setExpanded(!isExpanded);
      });
    });
  })();

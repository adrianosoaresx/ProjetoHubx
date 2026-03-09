    (function () {
      function initAccordion(accordionId, { hashPrefixes = [] } = {}) {
        const accordion = document.getElementById(accordionId);
        if (!accordion) {
          return;
        }

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

        const hash = window.location.hash;
        let hashTarget = null;
        const matchesPrefix = hashPrefixes.some((prefix) => {
          if (hash && hash.startsWith(prefix)) {
            hashTarget = document.querySelector(hash);
            return true;
          }
          return false;
        });

        const initialExpanded = toggle.getAttribute('aria-expanded') === 'true';
        const shouldExpandFromHash = hash === `#${accordionId}` || matchesPrefix;
        setExpanded(shouldExpandFromHash || initialExpanded);

        if (hashTarget instanceof HTMLElement) {
          requestAnimationFrame(() => {
            hashTarget.focus({ preventScroll: true });
            hashTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        } else if (shouldExpandFromHash) {
          panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        toggle.addEventListener('click', () => {
          const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
          setExpanded(!isExpanded);
        });
      }

      initAccordion('perfil-posts-accordion', { hashPrefixes: ['#post-'] });
      initAccordion('perfil-ratings-accordion');
    })();
  

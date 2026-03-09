    document.addEventListener('DOMContentLoaded', () => {
      const portfolioRoots = document.querySelectorAll('[data-portfolio-root]');
      portfolioRoots.forEach((root) => {
        const nucleoId = root.getAttribute('data-nucleo-id') || 'nucleo';
        const highlightStorageKey = `nucleoPortfolioHighlights:${nucleoId}`;
        const accordionStorageKey = `nucleoPortfolioAccordion:${nucleoId}`;
        const list = root.querySelector('[data-portfolio-list]');
        const buttons = root.querySelectorAll('[data-highlight-toggle]');
        const details = root.querySelector('details');
        const shouldForceOpen = root.dataset.portfolioForceOpen === 'true';

        if (details) {
          const readAccordionState = () => {
            try {
              const stored = localStorage.getItem(accordionStorageKey);
              if (stored === 'open' || stored === 'closed') {
                return stored;
              }
            } catch (error) {
              console.warn('Não foi possível ler o estado do portfólio do núcleo.', error);
            }
            return null;
          };

          const persistAccordionState = (isOpen) => {
            try {
              localStorage.setItem(accordionStorageKey, isOpen ? 'open' : 'closed');
            } catch (error) {
              console.warn('Não foi possível salvar o estado do portfólio do núcleo.', error);
            }
          };

          const storedAccordionState = readAccordionState();
          if (shouldForceOpen) {
            details.open = true;
            persistAccordionState(true);
          } else if (storedAccordionState === 'open') {
            details.open = true;
          }

          details.addEventListener('toggle', () => {
            persistAccordionState(details.open);
          });
        }

        const readStored = () => {
          try {
            const stored = localStorage.getItem(highlightStorageKey);
            if (!stored) {
              return new Set();
            }
            const parsed = JSON.parse(stored);
            if (Array.isArray(parsed)) {
              return new Set(parsed.map(String));
            }
          } catch (error) {
            console.warn('Não foi possível ler os destaques do portfólio do núcleo.', error);
          }
          return new Set();
        };

        const highlightedIds = readStored();

        const persist = () => {
          try {
            localStorage.setItem(highlightStorageKey, JSON.stringify(Array.from(highlightedIds)));
          } catch (error) {
            console.warn('Não foi possível salvar os destaques do portfólio do núcleo.', error);
          }
        };

        const setButtonState = (button, isActive) => {
          const labelOn = button.dataset.highlightLabelOn || button.getAttribute('aria-label') || '';
          const labelOff = button.dataset.highlightLabelOff || button.getAttribute('aria-label') || '';
          button.setAttribute('aria-pressed', String(isActive));
          button.setAttribute('aria-label', isActive ? labelOn : labelOff);
          button.title = isActive ? labelOn : labelOff;
          button.classList.toggle('text-red-500', isActive);
          button.classList.toggle('text-[var(--text-secondary)]', !isActive);
          const iconOn = button.querySelector('[data-highlight-icon="on"]');
          const iconOff = button.querySelector('[data-highlight-icon="off"]');
          if (iconOn && iconOff) {
            iconOn.classList.toggle('hidden', !isActive);
            iconOff.classList.toggle('hidden', isActive);
          }
        };

        const sortCards = () => {
          if (!list) {
            return;
          }
          const cards = Array.from(list.querySelectorAll('[data-media-card]'));
          cards.sort((a, b) => {
            const aId = a.dataset.mediaId ? String(a.dataset.mediaId) : '';
            const bId = b.dataset.mediaId ? String(b.dataset.mediaId) : '';
            const aHighlighted = highlightedIds.has(aId);
            const bHighlighted = highlightedIds.has(bId);
            if (aHighlighted !== bHighlighted) {
              return aHighlighted ? -1 : 1;
            }
            const aDate = Date.parse(a.dataset.createdAt || '') || 0;
            const bDate = Date.parse(b.dataset.createdAt || '') || 0;
            return bDate - aDate;
          });
          cards.forEach((card) => list.appendChild(card));
        };

        buttons.forEach((button) => {
          const mediaId = button.dataset.mediaId;
          if (!mediaId) {
            return;
          }
          const isActive = highlightedIds.has(String(mediaId));
          setButtonState(button, isActive);
          button.addEventListener('click', () => {
            const key = String(mediaId);
            if (highlightedIds.has(key)) {
              highlightedIds.delete(key);
            } else {
              highlightedIds.add(key);
            }
            setButtonState(button, highlightedIds.has(key));
            persist();
            sortCards();
          });
        });

        sortCards();
      });
    });
  

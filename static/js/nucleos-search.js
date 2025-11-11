(function () {
  const form = document.querySelector('[data-nucleos-search-form]');
  if (!form) {
    return;
  }

  const input = form.querySelector('[data-nucleos-search-input]');
  const feedback = document.querySelector('[data-nucleos-search-feedback]');
  const sections = Array.from(document.querySelectorAll('[data-nucleos-section]'));

  const normalize = (value) => (value || '').trim();
  const foundTemplate = form.dataset.feedbackFoundTemplate || '';
  const notFoundTemplate = form.dataset.feedbackNotFoundTemplate || '';
  const initialTerm = normalize(form.dataset.initialSearchTerm);

  const parseTotal = (section) => {
    const raw = section.dataset.nucleosSectionTotal;
    if (!raw) {
      return 0;
    }
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  };

  const getTotalResults = () =>
    sections.reduce((sum, section) => sum + parseTotal(section), 0);

  const openSectionsForTerm = (term) => {
    const normalized = normalize(term);
    if (!normalized) {
      sections.forEach((section) => {
        if (section.dataset.searchOpen === 'true') {
          section.removeAttribute('open');
          delete section.dataset.searchOpen;
        }
      });
      return;
    }

    sections.forEach((section) => {
      const hasResults = parseTotal(section) > 0;
      if (hasResults) {
        section.setAttribute('open', '');
        section.dataset.searchOpen = 'true';
      } else if (section.dataset.searchOpen === 'true') {
        section.removeAttribute('open');
        delete section.dataset.searchOpen;
      }
    });
  };

  const renderFeedback = (term) => {
    if (!feedback) {
      return;
    }

    const normalized = normalize(term);

    if (!normalized) {
      feedback.textContent = '';
      feedback.hidden = true;
      return;
    }

    const totalResults = getTotalResults();
    const template = totalResults > 0 ? foundTemplate : notFoundTemplate;
    if (template) {
      feedback.textContent = template.replace(/__term__/g, normalized);
      feedback.hidden = false;
    } else {
      feedback.textContent = '';
      feedback.hidden = true;
    }
  };

  renderFeedback(initialTerm);
  openSectionsForTerm(initialTerm);

  if (input && feedback) {
    input.addEventListener('input', () => {
      if (!input.value.trim()) {
        feedback.textContent = '';
        feedback.hidden = true;
      }
    });
  }
})();

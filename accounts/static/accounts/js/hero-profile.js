  (function () {
    const defaultErrorMessage = gettext('Você não tem permissão para realizar esta ação.');

    function clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    }

    function computeStarStates(average) {
      const parsed = Number(average);
      const value = Number.isFinite(parsed) ? parsed : 0;
      const rounded = Math.round(value * 2) / 2;
      const clamped = clamp(rounded, 0, 5);
      const stars = [];

      for (let position = 1; position <= 5; position += 1) {
        const fullThreshold = position;
        const halfThreshold = position - 0.5;

        if (clamped >= fullThreshold) {
          stars.push('full');
        } else if (clamped >= halfThreshold) {
          stars.push('half');
        } else {
          stars.push('empty');
        }
      }

      return stars;
    }

    function createStarIcon(state) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 24 24');
      svg.setAttribute('aria-hidden', 'true');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '2');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');
      svg.classList.add('h-4', 'w-4');

      if (state === 'full') {
        svg.classList.add('text-[#FFD700]', 'fill-[#FFD700]');
        svg.setAttribute('fill', 'currentColor');
      } else if (state === 'half') {
        svg.classList.add('text-[#FFD700]');
        svg.setAttribute('fill', 'none');
      } else {
        svg.classList.add('text-[var(--text-muted)]');
        svg.setAttribute('fill', 'none');
      }

      const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      polygon.setAttribute('points', '12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2');
      svg.appendChild(polygon);
      return svg;
    }

    function renderStarStates(states) {
      const starsContainer = document.querySelector('[data-user-rating-stars]');
      if (!starsContainer) {
        return;
      }

      const fragment = document.createDocumentFragment();
      const starStates = Array.isArray(states) && states.length ? states : Array(5).fill('empty');

      starStates.forEach((state) => {
        const wrapper = document.createElement('span');
        wrapper.className = 'inline-flex';
        wrapper.dataset.ratingState = state;
        wrapper.appendChild(createStarIcon(state));
        fragment.appendChild(wrapper);
      });

      starsContainer.innerHTML = '';
      starsContainer.appendChild(fragment);
    }

    function handleUserRatingSubmitted(event) {
      const detail = event.detail || {};
      const valueEl = document.querySelector('[data-user-rating-value]');
      const emptyEl = document.querySelector('[data-user-rating-empty]');
      const countEl = document.querySelector('[data-user-rating-count]');

      if (valueEl) {
        const display = detail.display || (typeof detail.average === 'number' ? detail.average.toFixed(1).replace('.', ',') : '');
        valueEl.textContent = display;
        valueEl.classList.toggle('hidden', !display);
      }

      if (emptyEl) {
        emptyEl.classList.add('hidden');
      }

      if (countEl && Object.prototype.hasOwnProperty.call(detail, 'total')) {
        countEl.textContent = `(${detail.total})`;
      }

      const actionButton = document.querySelector('[data-user-rating-action]');
      if (actionButton) {
        actionButton.remove();
      }

      if (Object.prototype.hasOwnProperty.call(detail, 'average')) {
        const states = computeStarStates(detail.average);
        renderStarStates(states);
      }

      const modal = document.getElementById('modal');
      if (modal) {
        modal.innerHTML = '';
      }
    }

    function showUserRatingMessage(message) {
      const displayMessage = typeof message === 'string' && message.trim()
        ? message.trim()
        : defaultErrorMessage;

      if (typeof window.HubxToast === 'function') {
        window.HubxToast(displayMessage);
      }
    }

    function handleUserRatingError(event) {
      const detail = event.detail || {};
      showUserRatingMessage(detail.message);
    }

    document.addEventListener('user-rating:submitted', handleUserRatingSubmitted);
    document.addEventListener('user-rating:error', handleUserRatingError);
  })();

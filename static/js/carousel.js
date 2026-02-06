(function () {
  const initialized = new WeakSet();

  function parsePositiveInt(value, fallback) {
    const parsed = parseInt(String(value ?? ''), 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      return parsed;
    }
    return fallback;
  }

  function getSlides(track) {
    return Array.from(track.querySelectorAll('[data-carousel-page]')).filter((slide) => {
      if (!(slide instanceof HTMLElement)) {
        return false;
      }
      if (slide.offsetParent !== null) {
        return true;
      }
      const rects = slide.getClientRects();
      return rects.length > 0;
    });
  }

  function buildRequestUrl(root, page) {
    const fetchUrl = root.dataset.fetchUrl || '';
    if (!fetchUrl) {
      return null;
    }
    const url = new URL(fetchUrl, window.location.origin);
    const section = root.dataset.section || '';
    const searchTerm = root.dataset.searchTerm || '';
    const searchParam = root.dataset.searchParam || 'search';
    const papel = root.dataset.papel || '';
    const card = root.dataset.card || '';
    const nucleoPublicId = root.dataset.nucleoPublicId || '';
    const eventoId = root.dataset.eventoId || '';
    const classificacao = root.dataset.classificacao || '';
    const scope = root.dataset.scope || '';
    const ownership = root.dataset.ownership || '';
    const statusFilter = root.dataset.statusFilter || '';
    const tipoFilter = root.dataset.tipoFilter || '';
    const showPromoteButton =
      root.hasAttribute('data-show-promote-button') &&
      (root.dataset.showPromoteButton || 'true').toLowerCase() !== 'false';

    url.searchParams.set('page', String(page));
    if (section) {
      url.searchParams.set('section', section);
    }
    if (searchTerm) {
      url.searchParams.set(searchParam, searchTerm);
    }
    if (papel) {
      url.searchParams.set('papel', papel);
    }
    if (card) {
      url.searchParams.set('card', card);
    }
    if (nucleoPublicId) {
      url.searchParams.set('nucleo_public_id', nucleoPublicId);
    }
    if (eventoId) {
      url.searchParams.set('evento_id', eventoId);
    }
    if (classificacao) {
      url.searchParams.set('classificacao', classificacao);
    }
    if (scope) {
      url.searchParams.set('scope', scope);
    }
    if (ownership) {
      url.searchParams.set('ownership', ownership);
    }
    if (statusFilter) {
      url.searchParams.set('status', statusFilter);
    }
    if (tipoFilter) {
      url.searchParams.set('tipo', tipoFilter);
    }
    if (showPromoteButton) {
      url.searchParams.set('show_promote_button', 'true');
    }
    return url;
  }

  function initCarousel(root) {
    if (!root || initialized.has(root)) {
      return;
    }

    const track = root.querySelector('[data-carousel-track]');
    if (!track) {
      return;
    }

    const prev = root.querySelector('[data-carousel-prev]');
    const next = root.querySelector('[data-carousel-next]');
    const fetchUrl = root.dataset.fetchUrl || '';

    let currentSlide = parsePositiveInt(root.dataset.currentSlide, 1);
    let currentBackendPage = parsePositiveInt(root.dataset.backendPage, 1);
    let totalBackendPages = parsePositiveInt(root.dataset.backendTotalPages, 1);
    const loadedBackendPages = new Set([currentBackendPage]);
    let isLoading = false;

    function setTransform(slideIndex) {
      const slides = getSlides(track);
      if (!slides.length) {
        currentSlide = 1;
        root.dataset.currentSlide = String(currentSlide);
        track.style.transform = 'translateX(0)';
        return currentSlide;
      }
      const clampedIndex = Math.min(Math.max(slideIndex, 1), slides.length);
      currentSlide = clampedIndex;
      root.dataset.currentSlide = String(currentSlide);
      track.style.transform = `translateX(-${(clampedIndex - 1) * 100}%)`;
      return currentSlide;
    }

    function updateButtons() {
      const slides = getSlides(track);
      const hasSlides = slides.length > 0;
      if (prev) {
        prev.disabled = !hasSlides || isLoading || currentSlide <= 1;
      }
      if (next) {
        const slidesCount = slides.length;
        const reachedEnd = currentSlide >= slidesCount && currentBackendPage >= totalBackendPages;
        next.disabled = !hasSlides || isLoading || reachedEnd;
      }
    }

    async function ensureBackendPage(page) {
      if (!fetchUrl || loadedBackendPages.has(page) || page > totalBackendPages) {
        return [];
      }
      const requestUrl = buildRequestUrl(root, page);
      if (!requestUrl) {
        return [];
      }
      isLoading = true;
      updateButtons();
      try {
        const response = await fetch(requestUrl.toString(), {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) {
          throw new Error('Request failed');
        }
        const payload = await response.json();
        const parsedTotal = parsePositiveInt(payload.total_pages, totalBackendPages);
        totalBackendPages = Math.max(parsedTotal, 1);
        root.dataset.backendTotalPages = String(totalBackendPages);
        const template = document.createElement('template');
        template.innerHTML = payload.html || '';
        const newSlides = Array.from(template.content.querySelectorAll('[data-carousel-page]'));
        newSlides.forEach((slide) => {
          if (slide instanceof HTMLElement) {
            slide.classList.add('flex-shrink-0');
          }
          track.appendChild(slide);
        });
        loadedBackendPages.add(page);
        currentBackendPage = Math.max(currentBackendPage, page);
        root.dataset.backendPage = String(currentBackendPage);
        setTransform(currentSlide);
        updateButtons();
        return newSlides;
      } catch (error) {
        console.error(error);
        throw error;
      } finally {
        isLoading = false;
        updateButtons();
      }
    }

    async function goToSlide(targetIndex) {
      if (isLoading) {
        return;
      }
      let desiredIndex = Math.max(targetIndex, 1);
      let slides = getSlides(track);
      if (!slides.length) {
        return;
      }
      while (desiredIndex > slides.length) {
        if (currentBackendPage >= totalBackendPages) {
          desiredIndex = slides.length;
          break;
        }
        try {
          await ensureBackendPage(currentBackendPage + 1);
        } catch (error) {
          return;
        }
        slides = getSlides(track);
        if (!slides.length) {
          return;
        }
      }

      slides = getSlides(track);
      if (!slides.length) {
        return;
      }

      const maxIndex = slides.length;
      desiredIndex = Math.min(desiredIndex, maxIndex);
      setTransform(desiredIndex);
      updateButtons();
    }

    if (prev) {
      prev.addEventListener('click', () => {
        if (!isLoading) {
          goToSlide(currentSlide - 1);
        }
      });
    }

    if (next) {
      next.addEventListener('click', () => {
        if (!isLoading) {
          goToSlide(currentSlide + 1);
        }
      });
    }

    const mediaQuery = typeof window.matchMedia === 'function' ? window.matchMedia('(min-width: 1024px)') : null;

    function handleBreakpointChange() {
      setTransform(currentSlide);
      updateButtons();
    }

    if (mediaQuery) {
      if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', handleBreakpointChange);
      } else if (typeof mediaQuery.addListener === 'function') {
        mediaQuery.addListener(handleBreakpointChange);
      }
    }

    window.addEventListener('resize', handleBreakpointChange);

    setTransform(currentSlide);
    updateButtons();

    initialized.add(root);
  }

  function initCarouselsWithin(element) {
    if (!element) {
      return;
    }
    if (element instanceof Document) {
      element.querySelectorAll('[data-carousel-root]').forEach(initCarousel);
      return;
    }
    if (element.matches && element.matches('[data-carousel-root]')) {
      initCarousel(element);
    }
    element.querySelectorAll?.('[data-carousel-root]').forEach((carousel) => {
      initCarousel(carousel);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initCarouselsWithin(document);
  });

  document.body?.addEventListener('htmx:afterSwap', (event) => {
    initCarouselsWithin(event.target);
  });
})();

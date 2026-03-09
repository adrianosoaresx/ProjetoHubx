const initEventoDetailPage = () => {
  if (document.body.dataset.eventoDetailInitialized === 'true') {
    return;
  }
  document.body.dataset.eventoDetailInitialized = 'true';
      const checkinRoot = document.querySelector('[data-checkin-root]');
      if (checkinRoot) {
        const scannerModal = document.getElementById('checkin-scanner-modal');
        const scannerClose = scannerModal?.querySelector('[data-checkin-close]');
        const scanButton = checkinRoot.querySelector('[data-checkin-scan-button]');
        const scannerContainer = document.getElementById('checkin-scanner');
        const scannerStatus = checkinRoot.querySelector('[data-checkin-status]');
        const feedbackModal = document.getElementById('checkin-feedback-modal');
        const feedbackContainer = feedbackModal?.querySelector('[data-checkin-feedback-container]');
        const feedbackMessage = feedbackModal?.querySelector('[data-checkin-feedback-message]');
        const feedbackClose = feedbackModal?.querySelector('[data-checkin-feedback-close]');
        let qrScanner = null;
        let scannerActive = false;
        let lastFocusedElement = null;
        let lastFeedbackTrigger = null;
        const scannerUnavailableMessage = gettext(
          'Leitor de QR Code indisponível. Verifique sua conexão ou as permissões da câmera.'
        );

        const setScanAvailabilityMessage = (message) => {
          if (!scannerStatus || !message) {
            return;
          }
          scannerStatus.textContent = message;
          scannerStatus.classList.remove('hidden');
        };

        const disableScanButton = (message) => {
          if (!scanButton) {
            return;
          }
          scanButton.disabled = true;
          scanButton.setAttribute('aria-disabled', 'true');
          scanButton.classList.add('cursor-not-allowed', 'opacity-60');
          if (message) {
            scanButton.setAttribute('aria-label', message);
            scanButton.title = message;
            setScanAvailabilityMessage(message);
          }
        };

        if (typeof Html5Qrcode === 'undefined') {
          disableScanButton(scannerUnavailableMessage);
          return;
        }

        const toggleModalVisibility = (modal, show, focusTarget) => {
          if (!modal) {
            return;
          }
          if (show) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            const target = focusTarget || modal;
            window.requestAnimationFrame(() => {
              if (target && typeof target.focus === 'function') {
                target.focus({ preventScroll: true });
              }
            });
          } else {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
          }
        };

        const getCsrfToken = () => {
          const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
          return match ? decodeURIComponent(match[1]) : '';
        };

        const ensureScanner = () => {
          if (typeof Html5Qrcode === 'undefined' || !scannerContainer) {
            disableScanButton(scannerUnavailableMessage);
            lastFeedbackTrigger = scanButton;
            showFeedback('error', scannerUnavailableMessage);
            return null;
          }
          if (!qrScanner) {
            qrScanner = new Html5Qrcode(scannerContainer.id);
          }
          return qrScanner;
        };

        const resetScannerView = () => {
          if (scannerContainer) {
            scannerContainer.innerHTML = '';
          }
        };

        const stopScanner = async () => {
          if (qrScanner && scannerActive) {
            try {
              await qrScanner.stop();
            } catch (error) {
              console.warn('Não foi possível parar o leitor de QR Code.', error);
            }
            try {
              await qrScanner.clear();
            } catch (error) {
              console.warn('Não foi possível limpar o leitor de QR Code.', error);
            }
          }
          scannerActive = false;
          resetScannerView();
        };

        const closeScanner = async () => {
          await stopScanner();
          toggleModalVisibility(scannerModal, false);
          if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
            lastFocusedElement.focus({ preventScroll: true });
          }
          lastFocusedElement = null;
        };

        const applyFeedbackStyles = (type) => {
          if (!feedbackContainer) {
            return;
          }
          const classesToRemove = [
            'border-[var(--color-success-200)]',
            'bg-[var(--color-success-500)]/10',
            'text-[var(--color-success-700)]',
            'border-[var(--color-danger-200)]',
            'bg-[var(--color-danger-500)]/10',
            'text-[var(--color-danger-700)]',
          ];
          feedbackContainer.classList.remove(...classesToRemove);
          if (type === 'success') {
            feedbackContainer.classList.add(
              'border-[var(--color-success-200)]',
              'bg-[var(--color-success-500)]/10',
              'text-[var(--color-success-700)]',
            );
          } else {
            feedbackContainer.classList.add(
              'border-[var(--color-danger-200)]',
              'bg-[var(--color-danger-500)]/10',
              'text-[var(--color-danger-700)]',
            );
          }
        };

        const showFeedback = (type, message) => {
          if (!feedbackModal || !feedbackMessage) {
            return;
          }
          feedbackMessage.textContent = message;
          applyFeedbackStyles(type);
          toggleModalVisibility(feedbackModal, true, feedbackClose);
        };

        const closeFeedback = () => {
          toggleModalVisibility(feedbackModal, false);
          if (lastFeedbackTrigger && typeof lastFeedbackTrigger.focus === 'function') {
            lastFeedbackTrigger.focus({ preventScroll: true });
          }
          lastFeedbackTrigger = null;
        };

        const buildCheckinUrl = (inscricaoId) => {
          const template = checkinRoot.dataset.checkinUrlTemplate || '';
          if (!template) {
            return null;
          }
          return template.replace(/\/0\/checkin\/$/, `/${inscricaoId}/checkin/`);
        };

        const parseInscricaoId = (codigo) => {
          const match =
            typeof codigo === 'string'
              ? codigo.match(/^inscricao:([^:]+)(?::.*)?$/)
              : null;
          return match ? match[1] : null;
        };

        const performCheckin = async (url, codigo) => {
          const csrfToken = getCsrfToken();
          try {
            const response = await fetch(url, {
              method: 'POST',
              headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
              },
              body: new URLSearchParams({ codigo }),
            });
            if (!response.ok) {
              const text = (await response.text()).trim();
              throw new Error(text || gettext('Não foi possível realizar o check-in.'));
            }
            let message = gettext('Check-in confirmado com sucesso.');
            try {
              const data = await response.json();
              if (data && typeof data.message === 'string' && data.message.trim()) {
                message = data.message;
              }
            } catch (error) {
              // Ignora erros de parsing do JSON
            }
            showFeedback('success', message);
            window.setTimeout(() => {
              window.location.reload();
            }, 1500);
          } catch (error) {
            const fallbackMessage = gettext('Não foi possível realizar o check-in.');
            showFeedback('error', error instanceof Error && error.message ? error.message : fallbackMessage);
          }
        };

        const handleScanSuccess = async (decodedText) => {
          await stopScanner();
          toggleModalVisibility(scannerModal, false);
          const inscricaoId = parseInscricaoId(decodedText);
          if (!inscricaoId) {
            lastFeedbackTrigger = scanButton;
            showFeedback('error', gettext('Código de check-in inválido.'));
            return;
          }
          const url = buildCheckinUrl(inscricaoId);
          if (!url) {
            lastFeedbackTrigger = scanButton;
            showFeedback('error', gettext('Não foi possível determinar o endpoint de check-in.'));
            return;
          }
          lastFeedbackTrigger = scanButton;
          await performCheckin(url, decodedText);
        };

        const extractErrorMessage = (error) => {
          if (!error) {
            return '';
          }
          if (typeof error === 'string') {
            return error;
          }
          if (error instanceof Error && error.message) {
            return error.message;
          }
          if (typeof error === 'object') {
            const { message, name } = error;
            if (typeof message === 'string' && message.trim()) {
              return message.trim();
            }
            if (typeof name === 'string' && name.trim()) {
              return name.trim();
            }
          }
          return '';
        };

        const startScanner = async () => {
          const scanner = ensureScanner();
          if (!scanner) {
            lastFeedbackTrigger = scanButton;
            showFeedback('error', scannerUnavailableMessage);
            return;
          }
          lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
          toggleModalVisibility(scannerModal, true, scannerClose);
          resetScannerView();
          try {
            let cameraId = null;
            try {
              const cameras = await Html5Qrcode.getCameras();
              if (!Array.isArray(cameras) || cameras.length === 0) {
                await stopScanner();
                toggleModalVisibility(scannerModal, false);
                lastFeedbackTrigger = scanButton;
                showFeedback('error', gettext('Nenhum dispositivo de câmera compatível foi encontrado.'));
                return;
              }
              const preferredCamera = cameras.find((camera) => {
                const label = typeof camera.label === 'string' ? camera.label.toLowerCase() : '';
                return label.includes('back') || label.includes('traseira');
              });
              cameraId = (preferredCamera || cameras[0]).id;
            } catch (cameraError) {
              console.warn('Não foi possível obter a lista de câmeras disponíveis.', cameraError);
            }

            const startConfig = { fps: 10, qrbox: 250 };
            if (cameraId) {
              await scanner.start(cameraId, startConfig, handleScanSuccess, () => {});
            } else {
              await scanner.start({ facingMode: 'environment' }, startConfig, handleScanSuccess, () => {});
            }
            scannerActive = true;
          } catch (error) {
            console.error('Não foi possível iniciar o leitor de QR Code.', error);
            await stopScanner();
            toggleModalVisibility(scannerModal, false);
            lastFeedbackTrigger = scanButton;
            const baseMessage = gettext('Não foi possível iniciar a câmera para leitura do QR Code.');
            const helpMessage = gettext(
              'Verifique sua conexão e se o navegador tem permissão para usar a câmera.'
            );
            const detailedMessage = extractErrorMessage(error);
            const message = detailedMessage
              ? `${baseMessage} ${helpMessage} ${gettext('Detalhes:')} ${detailedMessage}`
              : `${baseMessage} ${helpMessage}`;
            showFeedback('error', message);
          }
        };

        scanButton?.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          startScanner();
        });

        scannerClose?.addEventListener('click', (event) => {
          event.preventDefault();
          closeScanner();
        });

        scannerModal?.addEventListener('click', (event) => {
          if (event.target === scannerModal) {
            closeScanner();
          }
        });

        feedbackClose?.addEventListener('click', (event) => {
          event.preventDefault();
          closeFeedback();
        });

        feedbackModal?.addEventListener('click', (event) => {
          if (event.target === feedbackModal) {
            closeFeedback();
          }
        });

        document.addEventListener('keydown', (event) => {
          if (event.key !== 'Escape') {
            return;
          }
          if (scannerModal && !scannerModal.classList.contains('hidden')) {
            event.preventDefault();
            closeScanner();
            return;
          }
          if (feedbackModal && !feedbackModal.classList.contains('hidden')) {
            event.preventDefault();
            closeFeedback();
          }
        });
      }

      const portfolioRoots = document.querySelectorAll('[data-portfolio-root]');
      portfolioRoots.forEach((root) => {
        const eventId = root.getAttribute('data-event-id') || 'evento';
        const highlightStorageKey = `eventPortfolioHighlights:${eventId}`;
        const accordionStorageKey = `eventPortfolioAccordion:${eventId}`;
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
              console.warn('Não foi possível ler o estado do portfólio do evento.', error);
            }
            return null;
          };

          const persistAccordionState = (isOpen) => {
            try {
              localStorage.setItem(accordionStorageKey, isOpen ? 'open' : 'closed');
            } catch (error) {
              console.warn('Não foi possível salvar o estado do portfólio do evento.', error);
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
            console.warn('Não foi possível ler os destaques do evento.', error);
          }
          return new Set();
        };

        const highlightedIds = readStored();

        const persist = () => {
          try {
            localStorage.setItem(highlightStorageKey, JSON.stringify(Array.from(highlightedIds)));
          } catch (error) {
            console.warn('Não foi possível salvar os destaques do evento.', error);
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
};

if (window.Html5Qrcode) {
  initEventoDetailPage();
} else {
  document.addEventListener('html5-qrcode-ready', initEventoDetailPage, { once: true });
  document.addEventListener('DOMContentLoaded', initEventoDetailPage, { once: true });
}

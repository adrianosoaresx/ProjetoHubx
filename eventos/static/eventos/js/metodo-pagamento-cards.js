  (() => {
    const SELECTED_CLASSES = [
      "border-primary-500",
      "bg-primary-500/10",
      "ring-2",
      "ring-primary-500/60",
    ];

    const initializedGroups = new WeakSet();
    const initializedPixSections = new WeakSet();
    const faturarAccordionControllers = new WeakMap();
    const ACCORDION_HIDDEN_CLASS = 'hidden';
    const FATURAR_VALUE_PREFIX = 'faturar';

    let qrLibraryPromise = null;

    function getFaturarContainer(group) {
      if (!group) {
        return null;
      }
      return group.querySelector('[data-faturar-container]');
    }

    function updateFaturarContainerHighlight(group) {
      if (!group) {
        return;
      }
      const container = getFaturarContainer(group);
      if (!container) {
        return;
      }
      const isSelected = !!group.querySelector(
        'input[type="radio"][value^="faturar"]:checked'
      );
      SELECTED_CLASSES.forEach((className) => {
        container.classList.toggle(className, isSelected);
      });
    }

    function initFaturarAccordion(group) {
      const container = getFaturarContainer(group);
      if (!container) {
        return;
      }

      if (faturarAccordionControllers.has(container)) {
        const existing = faturarAccordionControllers.get(container);
        if (existing && typeof existing.refresh === 'function') {
          existing.refresh();
        }
        return;
      }

      const toggle = container.querySelector('[data-faturar-toggle]');
      const panel = container.querySelector('[data-faturar-panel]');
      if (!toggle || !panel) {
        return;
      }

      const indicator = toggle.querySelector('[data-state-indicator]');

      const controller = {
        expandedBySelection: false,
        setState(open, { fromSelection = false } = {}) {
          toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
          panel.classList.toggle(ACCORDION_HIDDEN_CLASS, !open);
          if (open) {
            panel.removeAttribute('aria-hidden');
          } else {
            panel.setAttribute('aria-hidden', 'true');
          }
          if (indicator) {
            indicator.setAttribute('data-state', open ? 'open' : 'closed');
          }
          if (fromSelection) {
            controller.expandedBySelection = open;
          }
        },
        isOpen() {
          return toggle.getAttribute('aria-expanded') === 'true';
        },
        openFromSelection() {
          controller.setState(true, { fromSelection: true });
        },
        closeFromSelection() {
          controller.setState(false, { fromSelection: true });
        },
        refresh() {
          const selectedInput = container.querySelector(
            'input[type="radio"][value^="faturar"]:checked'
          );
          controller.setState(!!selectedInput);
          controller.expandedBySelection = !!selectedInput;
        },
      };

      toggle.addEventListener('click', () => {
        const isExpanded = controller.isOpen();
        controller.setState(!isExpanded);
        if (!isExpanded) {
          controller.expandedBySelection = false;
        }
      });

      faturarAccordionControllers.set(container, controller);
      controller.refresh();
    }

    function toggleAccordion(card, open) {
      const accordion = card.querySelector('[data-payment-card-accordion]');
      if (!accordion) {
        return;
      }
      accordion.classList.toggle(ACCORDION_HIDDEN_CLASS, !open);
      if (open) {
        accordion.removeAttribute('aria-hidden');
      } else {
        accordion.setAttribute('aria-hidden', 'true');
        const pixPanel = accordion.querySelector('[data-pix-qrcode-panel]');
        if (pixPanel) {
          pixPanel.classList.add(ACCORDION_HIDDEN_CLASS);
          pixPanel.setAttribute('aria-hidden', 'true');
        }
        const pixButton = accordion.querySelector('[data-pix-qrcode-button]');
        if (pixButton) {
          pixButton.setAttribute('aria-expanded', 'false');
          const indicator = pixButton.querySelector('[data-state-indicator]');
          if (indicator) {
            indicator.setAttribute('data-state', 'closed');
          }
        }
        const pixKeyPanel = accordion.querySelector('[data-pix-key-panel]');
        if (pixKeyPanel) {
          pixKeyPanel.classList.add(ACCORDION_HIDDEN_CLASS);
          pixKeyPanel.setAttribute('aria-hidden', 'true');
        }
        const pixKeyButton = accordion.querySelector('[data-pix-key-button]');
        if (pixKeyButton) {
          pixKeyButton.setAttribute('aria-expanded', 'false');
          const indicator = pixKeyButton.querySelector('[data-state-indicator]');
          if (indicator) {
            indicator.setAttribute('data-state', 'closed');
          }
        }
      }
    }

    function updatePaymentProofVisibility(group, { emitEvent = true } = {}) {
      if (!group) {
        return;
      }

      const form = group.closest('form');
      if (!form) {
        return;
      }

      const proofField = form.querySelector('[data-payment-proof-field]');
      if (!proofField) {
        return;
      }

      const selectedInput = group.querySelector('input[type="radio"]:checked');
      const shouldHide = !!(
        selectedInput &&
        typeof selectedInput.value === 'string' &&
        selectedInput.value.startsWith('faturar')
      );

      proofField.classList.toggle('hidden', shouldHide);
      if (shouldHide) {
        proofField.setAttribute('aria-hidden', 'true');
      } else {
        proofField.removeAttribute('aria-hidden');
      }

      const fileInput = proofField.querySelector('[data-payment-proof-input]');
      const clearCheckbox = proofField.querySelector('[data-payment-proof-clear]');
      if (fileInput) {
        if (fileInput.dataset.originalRequired === undefined) {
          fileInput.dataset.originalRequired = fileInput.hasAttribute('required') ? 'true' : 'false';
        }

        if (shouldHide) {
          fileInput.removeAttribute('required');
          fileInput.value = '';
          if (clearCheckbox) {
            clearCheckbox.checked = false;
          }
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (fileInput.dataset.originalRequired === 'true') {
          fileInput.setAttribute('required', 'required');
        }
      }

      const detail = {
        value: selectedInput ? selectedInput.value : null,
        hidden: shouldHide,
        container: proofField,
      };

      document.dispatchEvent(
        new CustomEvent('payment-proof-visibility-change', { detail })
      );

      if (emitEvent) {
        document.dispatchEvent(new CustomEvent('payment-method-change', { detail }));
      }
    }

    function updateCardState(card) {
      const input = card.querySelector('input[type="radio"]');
      const body = card.querySelector('[data-payment-card-body]');
      if (!body || !input) {
        return;
      }

      const isChecked = input.checked;
      SELECTED_CLASSES.forEach((className) => {
        body.classList.toggle(className, isChecked);
      });
      toggleAccordion(card, isChecked);
    }

    function clearOtherSelections(cards, currentInput) {
      cards.forEach((card) => {
        const input = card.querySelector('input[type="radio"]');
        if (input && input !== currentInput) {
          input.checked = false;
          updateCardState(card);
        }
      });
    }

    function formatCurrency(value) {
      if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
        return '-';
      }
      try {
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(value);
      } catch (err) {
        return value.toFixed(2);
      }
    }

    function createPixPayload({ key, amount, description }) {
      const parts = ['PIX'];
      const cleanedKey = (key || '').toString().trim();
      if (cleanedKey) {
        parts.push(`chave=${cleanedKey}`);
      }
      if (typeof amount === 'number' && Number.isFinite(amount) && amount > 0) {
        parts.push(`valor=${amount.toFixed(2)}`);
      }
      const cleanedDescription = (description || '').toString().trim();
      if (cleanedDescription) {
        parts.push(`descricao=${cleanedDescription}`);
      }
      return parts.join('|');
    }

    function ensureQRCodeLibrary() {
      if (window.QRCode) {
        return Promise.resolve(window.QRCode);
      }
      if (!qrLibraryPromise) {
        qrLibraryPromise = new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';
          script.async = true;
          script.onload = () => {
            if (window.QRCode) {
              resolve(window.QRCode);
            } else {
              reject(new Error('QRCode library did not expose QRCode constructor.'));
            }
          };
          script.onerror = () => reject(new Error('Failed to load QRCode library.'));
          document.head.appendChild(script);
        });
      }
      return qrLibraryPromise;
    }

    function decodeUnicodeEscapes(value) {
      if (typeof value !== 'string') {
        return value;
      }
      return value.replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) => {
        const code = parseInt(hex, 16);
        if (Number.isNaN(code)) {
          return _;
        }
        return String.fromCharCode(code);
      });
    }

    async function renderPixQrCode(section) {
      const panel = section.querySelector('[data-pix-qrcode-panel]');
      if (!panel) {
        return;
      }
      const qrContainer = panel.querySelector('[data-pix-qr-container]');
      const amountContainer = panel.querySelector('[data-pix-qrcode-amount]');
      const keyContainer = panel.querySelector('[data-pix-qrcode-key]');

      const rawAmount = parseFloat(section.dataset.pixAmount || '0');
      const amount = Number.isFinite(rawAmount) ? rawAmount : 0;
      const pixKey = decodeUnicodeEscapes(section.dataset.pixKey || '').trim();
      const description = decodeUnicodeEscapes(section.dataset.pixEventTitle || '');
      const fallbackMessage = section.dataset.copyMissingText || '';
      const qrErrorMessage = section.dataset.qrErrorText || fallbackMessage || '';

      if (amountContainer) {
        amountContainer.textContent = formatCurrency(amount);
      }
      if (keyContainer) {
        keyContainer.textContent = pixKey || '-';
      }

      if (!qrContainer) {
        return;
      }

      qrContainer.innerHTML = '';
      qrContainer.setAttribute('aria-busy', 'true');

      if (!pixKey) {
        if (fallbackMessage) {
          const message = document.createElement('p');
          message.className = 'text-sm text-[var(--text-secondary)]';
          message.textContent = fallbackMessage;
          qrContainer.appendChild(message);
        }
        qrContainer.setAttribute('aria-busy', 'false');
        return;
      }

      try {
        const QRCodeClass = await ensureQRCodeLibrary();
        if (!QRCodeClass) {
          throw new Error('QRCode constructor unavailable.');
        }

        const payload = createPixPayload({ key: pixKey, amount, description });
        const qrOptions = {
          text: payload,
          width: 192,
          height: 192,
          colorDark: '#000000',
          colorLight: '#ffffff',
        };
        if (QRCodeClass.CorrectLevel && QRCodeClass.CorrectLevel.M) {
          qrOptions.correctLevel = QRCodeClass.CorrectLevel.M;
        }

        new QRCodeClass(qrContainer, qrOptions);
        qrContainer.setAttribute('aria-busy', 'false');
      } catch (err) {
        qrContainer.setAttribute('aria-busy', 'false');
        const errorElement = document.createElement('p');
        errorElement.className = 'text-sm text-red-500';
        errorElement.textContent = qrErrorMessage || '';
        qrContainer.appendChild(errorElement);
      }
    }

    function togglePixKeyPanel(section) {
      const keyButton = section.querySelector('[data-pix-key-button]');
      const keyPanel = section.querySelector('[data-pix-key-panel]');
      if (!keyButton || !keyPanel) {
        return;
      }

      const indicator = keyButton.querySelector('[data-state-indicator]');
      const keyDisplay = keyPanel.querySelector('[data-pix-key-display]');
      const fallbackMessage = section.dataset.copyMissingText || '';

      function updateKeyDisplay() {
        if (!keyDisplay) {
          return;
        }
        const pixKey = decodeUnicodeEscapes(section.dataset.pixKey || '').trim();
        keyDisplay.textContent = pixKey || fallbackMessage || '-';
      }

      function setKeyPanelState(isOpen) {
        keyButton.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        keyPanel.classList.toggle(ACCORDION_HIDDEN_CLASS, !isOpen);
        if (isOpen) {
          keyPanel.removeAttribute('aria-hidden');
          updateKeyDisplay();
        } else {
          keyPanel.setAttribute('aria-hidden', 'true');
        }
        if (indicator) {
          indicator.setAttribute('data-state', isOpen ? 'open' : 'closed');
        }
      }

      updateKeyDisplay();
      setKeyPanelState(false);

      keyButton.addEventListener('click', () => {
        const isExpanded = keyButton.getAttribute('aria-expanded') === 'true';
        setKeyPanelState(!isExpanded);
      });
    }

    function togglePixQrPanel(section) {
      const qrButton = section.querySelector('[data-pix-qrcode-button]');
      const panel = section.querySelector('[data-pix-qrcode-panel]');
      if (!qrButton || !panel) {
        return;
      }

      qrButton.addEventListener('click', async () => {
        const isHidden = panel.classList.contains(ACCORDION_HIDDEN_CLASS);
        const indicator = qrButton.querySelector('[data-state-indicator]');
        if (isHidden) {
          panel.classList.remove(ACCORDION_HIDDEN_CLASS);
          panel.removeAttribute('aria-hidden');
          qrButton.setAttribute('aria-expanded', 'true');
          if (indicator) {
            indicator.setAttribute('data-state', 'open');
          }
          await renderPixQrCode(section);
        } else {
          panel.classList.add(ACCORDION_HIDDEN_CLASS);
          panel.setAttribute('aria-hidden', 'true');
          qrButton.setAttribute('aria-expanded', 'false');
          if (indicator) {
            indicator.setAttribute('data-state', 'closed');
          }
        }
      });
    }

    function showPixFeedback(section, message, { isError = false } = {}) {
      const feedback = section.querySelector('[data-pix-feedback]');
      if (!feedback) {
        return;
      }
      feedback.textContent = message || '';
      feedback.classList.remove('hidden');
      if (isError) {
        feedback.classList.add('text-red-500');
        feedback.classList.remove('text-primary-600');
      } else {
        feedback.classList.add('text-primary-600');
        feedback.classList.remove('text-red-500');
      }
      setTimeout(() => {
        feedback.classList.add('hidden');
      }, 4000);
    }

    async function copyPixKey(section) {
      const pixKey = decodeUnicodeEscapes(section.dataset.pixKey || '').trim();
      const successMessage = section.dataset.copySuccessText || '';
      const errorMessage = section.dataset.copyErrorText || '';
      const missingMessage = section.dataset.copyMissingText || '';

      if (!pixKey) {
        showPixFeedback(section, missingMessage, { isError: true });
        return;
      }

      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(pixKey);
        } else {
          const textarea = document.createElement('textarea');
          textarea.value = pixKey;
          textarea.setAttribute('readonly', '');
          textarea.style.position = 'absolute';
          textarea.style.left = '-9999px';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        }
        showPixFeedback(section, successMessage, { isError: false });
      } catch (err) {
        showPixFeedback(section, errorMessage || missingMessage, { isError: true });
      }
    }

    function initPixSection(root) {
      const sections = (root || document).querySelectorAll('[data-pix-section]');
      sections.forEach((section) => {
        if (initializedPixSections.has(section)) {
          return;
        }
        const copyButton = section.querySelector('[data-pix-copy-button]');
        if (copyButton) {
          copyButton.addEventListener('click', () => {
            copyPixKey(section);
          });
        }
        togglePixKeyPanel(section);
        togglePixQrPanel(section);
        initializedPixSections.add(section);
      });
    }

    function initPaymentGroup(group) {
      if (!group || initializedGroups.has(group)) {
        return;
      }

      const cards = Array.from(group.querySelectorAll('[data-payment-card]'));
      if (!cards.length) {
        return;
      }

      cards.forEach((card) => {
        const input = card.querySelector('input[type="radio"]');
        if (!input) {
          return;
        }

        card.addEventListener('click', () => {
          if (input.disabled) {
            return;
          }
          if (!input.checked) {
            input.checked = true;
            input.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });

        input.addEventListener('change', () => {
          if (!input.checked) {
            return;
          }
          clearOtherSelections(cards, input);
          updateCardState(card);
          updatePaymentProofVisibility(group);
          updateFaturarContainerHighlight(group);
          const faturarContainer = getFaturarContainer(group);
          if (faturarContainer) {
            const controller = faturarAccordionControllers.get(faturarContainer);
            if (controller) {
              const isFaturarValue =
                typeof input.value === 'string' &&
                input.value.startsWith(FATURAR_VALUE_PREFIX);
              if (isFaturarValue) {
                controller.openFromSelection();
              } else if (controller.expandedBySelection) {
                controller.closeFromSelection();
              }
            }
          }
        });

        updateCardState(card);
      });

      initFaturarAccordion(group);
      updateFaturarContainerHighlight(group);
      updatePaymentProofVisibility(group, { emitEvent: false });
      initPixSection(group);

      initializedGroups.add(group);
    }

    function initAll(root) {
      const groups = (root || document).querySelectorAll('[data-payment-method-cards]');
      groups.forEach((group) => initPaymentGroup(group));
      initPixSection(root || document);
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => initAll(document));
    } else {
      initAll(document);
    }

    document.addEventListener('htmx:afterSwap', (event) => {
      initAll(event.target);
    });
  })();

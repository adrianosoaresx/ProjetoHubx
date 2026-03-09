      (() => {
        const initializedProofs = new WeakSet();
        const parseExts = (raw) => String(raw || '').split(',').map((item) => item.trim().toLowerCase()).filter(Boolean);
        const toMb = (bytes) => Math.round((Number(bytes || 0) / (1024 * 1024)) * 10) / 10;
        const formatExts = (exts) => exts.map((ext) => ext.replace('.', '').toUpperCase()).join(', ');

        function validateProof(file, input) {
          const imageExts = parseExts(input?.dataset.uploadImageExts);
          const pdfExts = parseExts(input?.dataset.uploadPdfExts);
          const ext = file.name && file.name.includes('.') ? `.${file.name.split('.').pop().toLowerCase()}` : '';
          const isImage = String(file.type || '').startsWith('image/') || imageExts.includes(ext);
          const isPdf = String(file.type || '') === 'application/pdf' || pdfExts.includes(ext);

          if (!isImage && !isPdf) {
            return `Tipo aceito: ${formatExts([...imageExts, ...pdfExts])}.`;
          }

          const maxBytes = isPdf
            ? Number(input?.dataset.uploadPdfMaxBytes || 0)
            : Number(input?.dataset.uploadImageMaxBytes || 0);
          const accepted = isPdf ? pdfExts : imageExts;
          if (maxBytes > 0 && file.size > maxBytes) {
            return `Tipo aceito: ${formatExts(accepted)}. Limite: ${toMb(maxBytes)}MB.`;
          }
          return '';
        }

        function updateDisplay(container) {
          if (!container) {
            return;
          }

          const text = container.querySelector('[data-payment-proof-text]');
          const defaultText = text?.dataset.defaultText || '';
          const initialText = text?.dataset.initialText || '';
          const preview = container.querySelector('[data-payment-proof-preview]');
          const initialUrl = preview?.dataset.initialUrl || '';
          const removeButton = container.querySelector('[data-payment-proof-remove]');
          const input = container.querySelector('[data-payment-proof-input]');
          const clearCheckbox = container.querySelector('[data-payment-proof-clear]');

          const files = input?.files;
          const hasFiles = !!(files && files.length > 0);
          const clearActive = !!(clearCheckbox && clearCheckbox.checked);
          const shouldShowInitial = !!(initialText && !hasFiles && !clearActive);

          if (text) {
            if (hasFiles) {
              const names = Array.from(files)
                .map((file) => file.name)
                .join(', ');
              text.textContent = names;
            } else if (shouldShowInitial) {
              text.textContent = initialText;
            } else {
              text.textContent = defaultText;
            }
          }

          if (preview) {
            if (shouldShowInitial && initialUrl) {
              preview.classList.remove('hidden');
              if (preview.tagName === 'A') {
                preview.setAttribute('href', initialUrl);
              }
            } else {
              preview.classList.add('hidden');
            }
          }

          if (removeButton) {
            const shouldShowRemove = hasFiles || shouldShowInitial;
            removeButton.classList.toggle('hidden', !shouldShowRemove);
          }
        }

        function clearSelection(container, { preserveInitial = false } = {}) {
          const input = container.querySelector('[data-payment-proof-input]');
          const clearCheckbox = container.querySelector('[data-payment-proof-clear]');
          const text = container.querySelector('[data-payment-proof-text]');
          const hasInitial = !!(text && text.dataset.initialText);

          if (input) {
            input.value = '';
            input.dispatchEvent(new Event('change', { bubbles: true }));
          }

          if (clearCheckbox) {
            if (preserveInitial) {
              clearCheckbox.checked = false;
            } else {
              clearCheckbox.checked = hasInitial;
            }
          }

          updateDisplay(container);
        }

        function initPaymentProof(container) {
          if (!container || initializedProofs.has(container)) {
            return;
          }

          const input = container.querySelector('[data-payment-proof-input]');
          const removeButton = container.querySelector('[data-payment-proof-remove]');
          const clearCheckbox = container.querySelector('[data-payment-proof-clear]');

          if (input) {
            input.addEventListener('change', () => {
              if (clearCheckbox) {
                clearCheckbox.checked = false;
              }
              const file = input.files && input.files[0];
              const validationMessage = file ? validateProof(file, input) : '';
              const text = container.querySelector('[data-payment-proof-text]');
              if (validationMessage) {
                input.value = '';
                if (text) {
                  text.textContent = validationMessage;
                }
              }
              updateDisplay(container);
            });
          }

          if (removeButton) {
            removeButton.addEventListener('click', () => {
              clearSelection(container);
            });
          }

          if (clearCheckbox) {
            clearCheckbox.addEventListener('change', () => {
              updateDisplay(container);
            });
          }

          updateDisplay(container);

          initializedProofs.add(container);
        }

        function initAll(root) {
          const containers = (root || document).querySelectorAll('[data-payment-proof-field]');
          containers.forEach((container) => initPaymentProof(container));
        }

        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', () => initAll(document));
        } else {
          initAll(document);
        }

        document.addEventListener('htmx:afterSwap', (event) => {
          initAll(event.target);
        });

        document.addEventListener('payment-proof-visibility-change', (event) => {
          const container = event.detail?.container;
          if (!container) {
            return;
          }
          if (event.detail.hidden) {
            clearSelection(container, { preserveInitial: true });
          } else {
            updateDisplay(container);
          }
        });
      })();
    

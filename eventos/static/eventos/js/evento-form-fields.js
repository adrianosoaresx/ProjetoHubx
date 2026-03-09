  (function () {
    const gratuitoField = document.querySelector('#id_gratuito');
    const publicoField = document.querySelector('#id_publico_alvo');
    const valorContainers = document.querySelectorAll('[data-valor-container]');

    const toggleValor = () => {
      valorContainers.forEach((container) => {
        if (!(container instanceof HTMLElement)) {
          return;
        }
        container.classList.remove('hidden');
        if (gratuitoField && gratuitoField.checked) {
          container.classList.add('hidden');
          return;
        }
        const publicoValue = publicoField ? publicoField.value : '';
        const target = container.dataset.valorContainer;
        if (publicoValue === '1' && target === 'associado') {
          container.classList.add('hidden');
        } else if (publicoValue === '2' && target === 'nucleado') {
          container.classList.add('hidden');
        }
      });
    };

    if (gratuitoField) {
      gratuitoField.addEventListener('change', toggleValor);
    }
    if (publicoField) {
      publicoField.addEventListener('change', toggleValor);
    }
    toggleValor();

    const accordions = document.querySelectorAll('[data-accordion]');
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
        const expanded = toggle.getAttribute('aria-expanded') === 'true';
        setExpanded(!expanded);
      });
    });

    const toMb = (bytes) => Math.round((Number(bytes || 0) / (1024 * 1024)) * 10) / 10;
    const parseExts = (raw) => String(raw || '').split(',').map((item) => item.trim().toLowerCase()).filter(Boolean);
    const formatExts = (exts) => exts.map((ext) => ext.replace('.', '').toUpperCase()).join(', ');

    const validateUpload = (file, input) => {
      const imageExts = parseExts(input.dataset.uploadImageExts);
      const pdfExts = parseExts(input.dataset.uploadPdfExts);
      const ext = file.name && file.name.includes('.') ? `.${file.name.split('.').pop().toLowerCase()}` : '';
      const isImage = String(file.type || '').startsWith('image/') || imageExts.includes(ext);
      const isPdf = String(file.type || '') === 'application/pdf' || pdfExts.includes(ext);

      if (isImage) {
        const maxBytes = Number(input.dataset.uploadImageMaxBytes || 0);
        if (maxBytes > 0 && file.size > maxBytes) {
          return `Tipo aceito: ${formatExts(imageExts)}. Limite: ${toMb(maxBytes)}MB.`;
        }
        return '';
      }
      if (isPdf) {
        const maxBytes = Number(input.dataset.uploadPdfMaxBytes || 0);
        if (maxBytes > 0 && file.size > maxBytes) {
          return `Tipo aceito: ${formatExts(pdfExts)}. Limite: ${toMb(maxBytes)}MB.`;
        }
        return '';
      }

      const accepted = [...imageExts, ...pdfExts];
      return `Tipo aceito: ${formatExts(accepted)}.`;
    };

    const setupFileInput = (input) => {
      if (!(input instanceof HTMLInputElement)) {
        return;
      }
      if (input.dataset.customFileBound === 'true') {
        return;
      }

      const wrapper = input.closest('[data-profile-file], [data-file-upload]');
      const status = wrapper
        ? wrapper.querySelector('[data-profile-file-name], [data-file-upload-name]')
        : null;
      const clearControl = wrapper
        ? wrapper.querySelector('[data-profile-file-clear], [data-file-upload-clear]')
        : null;
      const emptyText = input.dataset.emptyText || (status && status.dataset.emptyText) || '';
      const errorEl = wrapper
        ? wrapper.querySelector('[data-profile-file-error], [data-file-upload-error]')
        : null;

      if (status instanceof HTMLElement) {
        status.dataset.emptyText = status.dataset.emptyText || emptyText;
        status.dataset.originalText = status.dataset.originalText || status.textContent || '';
      }

      const updateStatus = () => {
        if (!(status instanceof HTMLElement)) {
          return;
        }
        const files = input.files;
        if (files && files.length) {
          const names = Array.from(files)
            .map((file) => (file && file.name ? file.name : ''))
            .filter(Boolean);
          status.textContent = names.length ? names.join(', ') : emptyText;
          return;
        }

        if (clearControl instanceof HTMLInputElement && clearControl.checked) {
          status.textContent = emptyText;
          return;
        }

        const originalText = status.dataset.originalText || '';
        status.textContent = originalText || emptyText;
      };

      updateStatus();

      input.addEventListener('change', () => {
        if (clearControl instanceof HTMLInputElement && input.files && input.files.length) {
          clearControl.checked = false;
        }
        const file = input.files && input.files[0];
        const validationMessage = file ? validateUpload(file, input) : '';
        if (validationMessage) {
          input.value = '';
          if (errorEl instanceof HTMLElement) {
            errorEl.textContent = validationMessage;
            errorEl.classList.remove('hidden');
          }
        } else if (errorEl instanceof HTMLElement) {
          errorEl.textContent = '';
          errorEl.classList.add('hidden');
        }
        updateStatus();
      });

      if (clearControl instanceof HTMLInputElement) {
        clearControl.addEventListener('change', () => {
          if (clearControl.checked) {
            input.value = '';
            const event = new Event('change');
            input.dispatchEvent(event);
            if (status instanceof HTMLElement) {
              status.textContent = emptyText;
            }
          } else if (status instanceof HTMLElement) {
            const originalText = status.dataset.originalText || '';
            status.textContent = originalText || emptyText;
          }
        });
      }

      input.dataset.customFileBound = 'true';
    };

    const fileInputs = document.querySelectorAll('[data-profile-file-input], [data-file-upload-input]');
    fileInputs.forEach((input) => setupFileInput(input));
  })();

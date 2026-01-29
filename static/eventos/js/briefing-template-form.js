(() => {
  const formSection = document.querySelector('[data-briefing-form]');
  if (!formSection) {
    return;
  }

  const textarea = formSection.querySelector('[data-estrutura-json]');
  const listEl = formSection.querySelector('[data-perguntas-list]');
  const emptyState = formSection.querySelector('[data-perguntas-empty]');
  const labelInput = formSection.querySelector('[data-pergunta-label]');
  const typeInput = formSection.querySelector('[data-pergunta-type]');
  const requiredInput = formSection.querySelector('[data-pergunta-required]');
  const optionsInput = formSection.querySelector('[data-pergunta-options]');
  const optionsWrapper = formSection.querySelector('[data-pergunta-options-wrapper]');
  const addButton = formSection.querySelector('[data-pergunta-add]');
  const errorMessage = formSection.querySelector('[data-pergunta-error]');
  const jsonToggle = formSection.querySelector('[data-json-toggle]');
  const jsonWrapper = formSection.querySelector('[data-json-wrapper]');

  let perguntas = [];
  let dragIndex = null;

  const showError = (message) => {
    if (!errorMessage) {
      return;
    }
    if (message) {
      errorMessage.textContent = message;
      errorMessage.removeAttribute('hidden');
    } else {
      errorMessage.textContent = '';
      errorMessage.setAttribute('hidden', 'hidden');
    }
  };

  const parseOptions = (value) => value
    .split(/\n|,/)
    .map((option) => option.trim())
    .filter(Boolean);

  const updateTextarea = () => {
    if (!textarea) {
      return;
    }
    textarea.value = JSON.stringify(perguntas, null, 2);
  };

  const toggleEmptyState = () => {
    if (!emptyState) {
      return;
    }
    if (perguntas.length === 0) {
      emptyState.classList.remove('hidden');
    } else {
      emptyState.classList.add('hidden');
    }
  };

  const handleRemove = (index) => {
    perguntas.splice(index, 1);
    renderList();
  };

  const handleDragStart = (index, event) => {
    dragIndex = index;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', String(index));
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (index, event) => {
    event.preventDefault();
    if (dragIndex === null || dragIndex === index) {
      return;
    }
    const [moved] = perguntas.splice(dragIndex, 1);
    perguntas.splice(index, 0, moved);
    dragIndex = null;
    renderList();
  };

  const renderList = () => {
    if (!listEl) {
      return;
    }
    listEl.innerHTML = '';
    perguntas.forEach((pergunta, index) => {
      const li = document.createElement('li');
      li.className = 'rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] p-3 space-y-2';
      li.setAttribute('draggable', 'true');
      li.dataset.index = String(index);

      const optionsText = Array.isArray(pergunta.options) && pergunta.options.length
        ? pergunta.options.join(', ')
        : '—';

      li.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="space-y-1">
            <p class="text-sm font-semibold text-[var(--text-primary)]">${pergunta.label}</p>
            <p class="text-xs text-[var(--text-secondary)]">Tipo: ${pergunta.type} • ${pergunta.required ? 'Obrigatório' : 'Opcional'}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-[var(--text-secondary)]">Arraste para reordenar</span>
            <button type="button" class="btn btn-link text-sm" data-remove>Remover</button>
          </div>
        </div>
        <p class="text-xs text-[var(--text-secondary)]">Opções: ${optionsText}</p>
      `;

      li.addEventListener('dragstart', (event) => handleDragStart(index, event));
      li.addEventListener('dragover', handleDragOver);
      li.addEventListener('drop', (event) => handleDrop(index, event));

      const removeButton = li.querySelector('[data-remove]');
      if (removeButton) {
        removeButton.addEventListener('click', () => handleRemove(index));
      }

      listEl.appendChild(li);
    });

    toggleEmptyState();
    updateTextarea();
  };

  const updateOptionsVisibility = () => {
    if (!optionsWrapper || !typeInput) {
      return;
    }
    if (typeInput.value === 'select') {
      optionsWrapper.classList.remove('hidden');
    } else {
      optionsWrapper.classList.add('hidden');
    }
  };

  const resetFormInputs = () => {
    if (labelInput) {
      labelInput.value = '';
    }
    if (typeInput) {
      typeInput.value = 'text';
    }
    if (requiredInput) {
      requiredInput.checked = false;
    }
    if (optionsInput) {
      optionsInput.value = '';
    }
    updateOptionsVisibility();
  };

  const addPergunta = () => {
    if (!labelInput || !typeInput || !requiredInput || !optionsInput) {
      return;
    }
    const label = labelInput.value.trim();
    if (!label) {
      showError('Informe um rótulo para a pergunta.');
      return;
    }
    const type = typeInput.value;
    const required = requiredInput.checked;
    const pergunta = { label, type, required };

    if (type === 'select') {
      const options = parseOptions(optionsInput.value);
      if (options.length === 0) {
        showError('Informe ao menos uma opção para perguntas do tipo seleção.');
        return;
      }
      pergunta.options = options;
    }

    perguntas.push(pergunta);
    showError('');
    resetFormInputs();
    renderList();
  };

  const loadInitialData = () => {
    if (!textarea || !textarea.value) {
      return;
    }
    try {
      const parsed = JSON.parse(textarea.value);
      if (Array.isArray(parsed)) {
        perguntas = parsed;
      }
    } catch (error) {
      showError('O JSON atual é inválido. Corrija no modo avançado.');
    }
  };

  if (jsonToggle && jsonWrapper) {
    jsonToggle.addEventListener('change', () => {
      if (jsonToggle.checked) {
        jsonWrapper.classList.remove('hidden');
      } else {
        jsonWrapper.classList.add('hidden');
      }
    });
  }

  if (typeInput) {
    typeInput.addEventListener('change', updateOptionsVisibility);
  }

  if (addButton) {
    addButton.addEventListener('click', addPergunta);
  }

  loadInitialData();
  updateOptionsVisibility();
  renderList();
})();

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
  const exampleButton = formSection.querySelector('[data-perguntas-example]');
  const examplePayload = formSection.querySelector('[data-estrutura-exemplo]');
  const structureError = formSection.querySelector('[data-estrutura-error]');
  const form = formSection.closest('form');

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

  const showStructureError = (message) => {
    if (!structureError) {
      return;
    }
    if (message) {
      structureError.textContent = message;
      structureError.removeAttribute('hidden');
    } else {
      structureError.textContent = '';
      structureError.setAttribute('hidden', 'hidden');
    }
  };

  const clearHighlightedError = () => {
    if (!listEl) {
      return;
    }
    const highlighted = listEl.querySelector('[data-error-highlight="true"]');
    if (highlighted) {
      highlighted.classList.remove('ring-2', 'ring-red-500');
      highlighted.removeAttribute('data-error-highlight');
      highlighted.removeAttribute('tabindex');
    }
  };

  const highlightErrorItem = (index) => {
    if (!listEl) {
      return;
    }
    clearHighlightedError();
    const item = listEl.querySelector(`[data-index="${index}"]`);
    if (item) {
      item.classList.add('ring-2', 'ring-red-500');
      item.setAttribute('data-error-highlight', 'true');
      item.setAttribute('tabindex', '-1');
      item.focus({ preventScroll: false });
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

  const validateEstrutura = (estrutura) => {
    if (!Array.isArray(estrutura)) {
      return { message: 'A estrutura deve ser uma lista de perguntas.' };
    }
    const allowedTypes = new Set(['text', 'textarea', 'number', 'email', 'date', 'select', 'boolean']);
    for (let index = 0; index < estrutura.length; index += 1) {
      const pergunta = estrutura[index];
      const displayIndex = index + 1;
      if (!pergunta || typeof pergunta !== 'object' || Array.isArray(pergunta)) {
        return {
          message: `A pergunta ${displayIndex} deve ser um objeto JSON válido.`,
          index,
          field: 'estrutura',
        };
      }
      for (const field of ['label', 'type', 'required']) {
        if (!(field in pergunta)) {
          return {
            message: `A pergunta ${displayIndex} precisa conter '${field}'.`,
            index,
            field,
          };
        }
      }
      const label = pergunta.label;
      if (typeof label !== 'string' || !label.trim()) {
        return {
          message: `Pergunta ${displayIndex}: rótulo inválido.`,
          index,
          field: 'label',
        };
      }
      const type = pergunta.type;
      if (typeof type !== 'string' || !allowedTypes.has(type)) {
        return {
          message: `Pergunta ${displayIndex}: tipo inválido.`,
          index,
          field: 'type',
        };
      }
      if (typeof pergunta.required !== 'boolean') {
        return {
          message: `Pergunta ${displayIndex}: o campo 'required' deve ser booleano.`,
          index,
          field: 'required',
        };
      }
      if (type === 'select') {
        const options = pergunta.options ?? pergunta.choices;
        if (!Array.isArray(options) || options.length === 0) {
          return {
            message: `Pergunta ${displayIndex}: informe opções para perguntas do tipo seleção.`,
            index,
            field: 'options',
          };
        }
      }
    }
    return null;
  };

  const validateFromTextarea = () => {
    if (!textarea || !textarea.value) {
      return validateEstrutura(perguntas);
    }
    try {
      const parsed = JSON.parse(textarea.value);
      return validateEstrutura(parsed);
    } catch (error) {
      return { message: 'O JSON atual é inválido. Corrija no modo avançado.' };
    }
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
    showStructureError('');
    clearHighlightedError();
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

  const parseExamplePerguntas = () => {
    if (!examplePayload) {
      return null;
    }
    try {
      const parsed = JSON.parse(examplePayload.textContent);
      return Array.isArray(parsed) ? parsed : null;
    } catch (error) {
      showError('Não foi possível carregar o exemplo. Atualize a página e tente novamente.');
      return null;
    }
  };

  const insertExamplePerguntas = () => {
    const example = parseExamplePerguntas();
    if (!example) {
      return;
    }
    perguntas = example.map((item) => ({ ...item }));
    showError('');
    showStructureError('');
    clearHighlightedError();
    renderList();
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

  if (exampleButton) {
    exampleButton.addEventListener('click', insertExamplePerguntas);
  }

  if (form) {
    form.addEventListener('submit', (event) => {
      const validationError = validateFromTextarea();
      if (validationError) {
        event.preventDefault();
        showStructureError(validationError.message);
        if (typeof validationError.index === 'number') {
          highlightErrorItem(validationError.index);
        } else {
          clearHighlightedError();
          if (jsonToggle && jsonWrapper) {
            jsonToggle.checked = true;
            jsonWrapper.classList.remove('hidden');
          }
          if (textarea) {
            textarea.focus({ preventScroll: false });
          }
        }
      } else {
        showStructureError('');
        clearHighlightedError();
      }
    });
  }

  loadInitialData();
  updateOptionsVisibility();
  renderList();
})();

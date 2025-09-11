// Feed JavaScript - Funcionalidades essenciais
function bindFeedEvents(root = document) {
  const textarea = root.querySelector('textarea[name="conteudo"]');
  const charCounter = root.querySelector("#char-count");

  if (textarea && charCounter) {
    const updateCharCounter = () => {
      const currentLength = textarea.value.length;
      const maxLength = 500;

      charCounter.textContent = currentLength;

      if (currentLength > maxLength * 0.9) {
        charCounter.style.color = "var(--danger-color)";
      } else if (currentLength > maxLength * 0.7) {
        charCounter.style.color = "var(--warning-color)";
      } else {
        charCounter.style.color = "var(--text-muted)";
      }
    };

    updateCharCounter();
    textarea.addEventListener("input", updateCharCounter);
  }

  const fileInput = root.querySelector('input[type="file"]');
  const fileText = root.querySelector(".file-text");

  if (fileInput && fileText) {
    const originalText = fileText.textContent;

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];

      if (file) {
        const selectedText = window.gettext
          ? gettext("Selecionado:")
          : "Selecionado:";
        fileText.textContent = `${selectedText} ${file.name}`;
        fileText.style.color = "var(--success-color)";
      } else {
        fileText.textContent = originalText;
        fileText.style.color = "var(--text-secondary)";
      }
    });
  }

  const postForm = root.querySelector(".post-form");

  if (postForm) {
    // Área de mensagens inline
    let msgArea = root.querySelector('#form-messages');
    if (!msgArea) {
      msgArea = document.createElement('div');
      msgArea.id = 'form-messages';
      msgArea.className = 'hidden';
      postForm.prepend(msgArea);
    }
    const showMsg = (text, variant = 'error') => {
      if (!msgArea) return;
      const base = 'rounded-xl text-sm p-3 mt-2';
      const styles =
        variant === 'error'
          ? 'border border-[var(--error-light)] bg-[var(--error-light)] text-[var(--error)]'
          : 'border border-[var(--primary-light)] bg-[var(--primary-light)] text-[var(--primary)]';
      msgArea.className = `${base} ${styles}`;
      msgArea.textContent = text;
      msgArea.classList.remove('hidden');
    };
    const clearMsg = () => {
      if (!msgArea) return;
      msgArea.className = 'hidden';
      msgArea.textContent = '';
    };
    postForm.addEventListener('submit', (e) => {
      clearMsg();
      const content = textarea ? textarea.value.trim() : '';
      const hasFile = fileInput && fileInput.files.length > 0;
      if (content.length === 0 && !hasFile) {
        e.preventDefault();
        const msg = window.gettext ? gettext('Por favor, escreva algo ou selecione um arquivo antes de publicar.') : 'Por favor, escreva algo ou selecione um arquivo antes de publicar.';
        showMsg(msg, 'error');
        if (textarea) textarea.focus();
        return false;
      }
      if (content.length > 500) {
        e.preventDefault();
        const msg = window.gettext ? gettext('O conteúdo deve ter no máximo 500 caracteres.') : 'O conteúdo deve ter no máximo 500 caracteres.';
        showMsg(msg, 'error');
        if (textarea) textarea.focus();
        return false;
      }
    });
  }

  if (textarea) {
    textarea.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 300) + "px";
    });
  }

  const tagsSelect = root.querySelector("#tags-select");
  const tagsHidden = root.querySelector("#tags");

  if (tagsSelect && tagsHidden) {
    tagsSelect.addEventListener("change", () => {
      const values = Array.from(tagsSelect.selectedOptions)
        .map((o) => o.value)
        .join(",");
      tagsHidden.value = values;
    });
  }

  // Visibilidade/Destino: sincroniza seleção de núcleo com tipo_feed
  const tipoGlobal = root.querySelector('input[name="tipo_feed"][value="global"]');
  const tipoUsuario = root.querySelector('input[name="tipo_feed"][value="usuario"]');
  const tipoNucleoHidden = root.querySelector('#tipo_feed_nucleo_hidden');
  const nucleoRadios = root.querySelectorAll('input[name="nucleo"]');
  if (nucleoRadios && tipoNucleoHidden) {
    nucleoRadios.forEach(r => {
      r.addEventListener('change', () => {
        if (r.checked) {
          // Marcar tipo_feed como "nucleo" quando escolher um núcleo
          tipoNucleoHidden.checked = true;
        }
      });
    });
  }
  const clearNucleos = () => {
    nucleoRadios.forEach(r => {
      r.checked = false;
    });
  };
  if (tipoGlobal) {
    tipoGlobal.addEventListener('change', () => {
      if (tipoGlobal.checked) clearNucleos();
    });
  }
  if (tipoUsuario) {
    tipoUsuario.addEventListener('change', () => {
      if (tipoUsuario.checked) clearNucleos();
    });
  }

  // Tags: chips input
  const tagsInput = root.querySelector('#tags-input');
  const chipsContainer = root.querySelector('#tags-chips');
  const tagsHiddenText = root.querySelector('#id_tags_text');
  const updateHiddenTags = () => {
    if (!chipsContainer || !tagsHiddenText) return;
    const values = Array.from(chipsContainer.querySelectorAll('[data-tag]')).map(n => n.getAttribute('data-tag'));
    tagsHiddenText.value = values.join(',');
  };
  const addChip = (text) => {
    const value = (text || '').trim();
    if (!value) return;
    // Evita duplicadas (case-insensitive)
    const exists = Array.from(chipsContainer.querySelectorAll('[data-tag]')).some(n => (n.getAttribute('data-tag')||'').toLowerCase() === value.toLowerCase());
    if (exists) return;
    const chip = document.createElement('span');
    chip.className =
      'inline-flex items-center gap-1 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-full px-3 py-1 text-xs';
    chip.setAttribute('data-tag', value);
    chip.innerHTML = `${value} <button type="button" class="ml-1 btn btn-danger btn-sm" aria-label="Remover">&times;</button>`;
    chip.querySelector('button').addEventListener('click', () => {
      chip.remove();
      updateHiddenTags();
    });
    chipsContainer.appendChild(chip);
    updateHiddenTags();
  };
  if (tagsInput && chipsContainer && tagsHiddenText) {
    // Pre-popular a partir do hidden (ex: após erro de validação)
    const initial = (tagsHiddenText.value || '').split(',').map(t => t.trim()).filter(Boolean);
    if (initial.length) {
      // Evita duplicatas caso o container já tenha itens
      chipsContainer.innerHTML = '';
      initial.forEach(addChip);
    }

    // Permite colar lista separada por vírgulas
    tagsInput.addEventListener('paste', (e) => {
      const txt = (e.clipboardData || window.clipboardData).getData('text');
      if (txt && txt.includes(',')) {
        e.preventDefault();
        txt.split(',').map(t => t.trim()).filter(Boolean).forEach(addChip);
        tagsInput.value = '';
      }
    });
    // Criar chip ao sair do campo com valor
    tagsInput.addEventListener('change', () => {
      if (tagsInput.value && tagsInput.value.trim()) {
        addChip(tagsInput.value);
        tagsInput.value = '';
      }
    });
    tagsInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addChip(tagsInput.value);
        tagsInput.value = '';
      } else if (e.key === 'Backspace' && !tagsInput.value) {
        const last = chipsContainer.querySelector('[data-tag]:last-child');
        if (last) {
          last.remove();
          updateHiddenTags();
        }
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindFeedEvents();
});

document.addEventListener("htmx:load", (e) => {
  bindFeedEvents(e.target);
});

document.addEventListener("htmx:afterSwap", (e) => {
  bindFeedEvents(e.target);
});

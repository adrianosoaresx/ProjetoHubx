// Feed JavaScript - Funcionalidades essenciais
const getCookie = (name) => {
  if (typeof document === 'undefined') {
    return null;
  }
  const cookies = document.cookie ? document.cookie.split('; ') : [];
  for (let i = 0; i < cookies.length; i += 1) {
    const [key, ...rest] = cookies[i].split('=');
    if (key === name) {
      return decodeURIComponent(rest.join('='));
    }
  }
  return null;
};

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

  const fileInputs = Array.from(root.querySelectorAll('input[type="file"]'));

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
      const hasFile = fileInputs.some((input) => input.files && input.files.length > 0);
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
      'inline-flex items-center gap-1 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-full px-3 py-1 text-xs normal-case ring-1 ring-inset ring-[var(--border-secondary)]';
    chip.setAttribute('data-tag', value);

    const label = document.createElement('span');
    label.textContent = value;
    label.className = 'leading-none';

    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    const removeLabelBase = window.gettext ? gettext('Remover') : 'Remover';
    removeButton.setAttribute('aria-label', `${removeLabelBase} ${value}`);
    removeButton.title = removeButton.getAttribute('aria-label');
    removeButton.className =
      'ml-2 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--error)] text-[var(--text-inverse)] transition-colors hover:bg-[var(--color-error-700)] focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--error-light)] focus-visible:ring-offset-[var(--bg-primary)]';
    removeButton.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5" aria-hidden="true">
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </svg>
    `;
    removeButton.addEventListener('click', () => {
      chip.remove();
      updateHiddenTags();
    });

    chip.appendChild(label);
    chip.appendChild(removeButton);
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

  // Checkboxes exclusivos (comportamento semelhante a rádio)
  const exclusiveCheckboxes = Array.from(root.querySelectorAll('input[type="checkbox"][data-exclusive]'));
  if (exclusiveCheckboxes.length) {
    const groups = exclusiveCheckboxes.reduce((acc, checkbox) => {
      const groupName = checkbox.getAttribute('data-exclusive');
      if (!groupName) {
        return acc;
      }
      if (!acc[groupName]) {
        acc[groupName] = [];
      }
      acc[groupName].push(checkbox);
      return acc;
    }, {});

    Object.values(groups).forEach((group) => {
      group.forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) {
            group.forEach((other) => {
              if (other !== checkbox) {
                other.checked = false;
              }
            });
          } else {
            const anyChecked = group.some((item) => item.checked);
            if (!anyChecked) {
              checkbox.checked = true;
            }
          }
        });
      });
    });
  }

  const csrfToken = getCookie('csrftoken');
  const bookmarkButtons = Array.from(root.querySelectorAll('.bookmark-btn'));
  if (bookmarkButtons.length) {
    bookmarkButtons.forEach((btn) => {
      if (btn.dataset.bookmarkBound === 'true') {
        return;
      }
      btn.dataset.bookmarkBound = 'true';
      btn.addEventListener('click', async (event) => {
        event.preventDefault();
        event.stopPropagation();
        const postId = btn.dataset.postId;
        if (!postId) {
          return;
        }
        try {
          const response = await fetch(`/api/feed/posts/${postId}/bookmark/`, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrfToken || '',
              'X-Requested-With': 'XMLHttpRequest',
            },
          });
          if (!response.ok) {
            throw new Error('bookmark failed');
          }
          const data = await response.json();
          const isBookmarked = Boolean(data.bookmarked);
          btn.classList.toggle('text-[var(--warning)]', isBookmarked);
          btn.setAttribute('aria-pressed', isBookmarked ? 'true' : 'false');
        } catch (error) {
          const message = window.gettext ? gettext('Erro ao salvar') : 'Erro ao salvar';
          window.alert(message);
        }
      });
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

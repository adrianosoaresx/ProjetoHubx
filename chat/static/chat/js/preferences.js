document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('preferences-modal');
  const openBtn = document.getElementById('open-preferences');
  const cancelBtn = document.getElementById('pref-cancel');
  const form = document.getElementById('preferences-form');
  const themeSelect = document.getElementById('pref-theme');
  const dailyCheckbox = document.getElementById('pref-daily');
  const weeklyCheckbox = document.getElementById('pref-weekly');
  const searchesInput = document.getElementById('pref-searches');
  const publicKeyInput = document.getElementById('pref-public-key');
  const saveKeyBtn = document.getElementById('pref-save-key');
  const keyStatus = document.getElementById('pref-key-status');
  const currentUserId = publicKeyInput ? publicKeyInput.dataset.userId : null;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  function applyTheme(theme) {
    document.documentElement.classList.toggle('dark', theme === 'escuro');
    localStorage.setItem('tema', theme);
    document.cookie = `tema=${theme};path=/`;
  }

  function loadPreferences() {
    fetch('/api/chat/preferences/')
      .then(resp => resp.json())
      .then(data => {
        themeSelect.value = data.tema || 'claro';
        dailyCheckbox.checked = !!data.resumo_diario;
        weeklyCheckbox.checked = !!data.resumo_semanal;
        searchesInput.value = (data.buscas_salvas || []).join(', ');
        applyTheme(data.tema);
      });
  }

  function loadPublicKey() {
    if (!publicKeyInput || !currentUserId) return;
    fetch(`/api/chat/usuarios/${currentUserId}/chave-publica/`)
      .then(resp => resp.json())
      .then(data => {
        publicKeyInput.value = data.chave_publica || '';
      });
  }

  if (openBtn) {
    openBtn.addEventListener('click', () => {
      modal.classList.remove('hidden');
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const payload = {
        tema: themeSelect.value,
        resumo_diario: dailyCheckbox.checked,
        resumo_semanal: weeklyCheckbox.checked,
        buscas_salvas: searchesInput.value
          ? searchesInput.value.split(',').map(s => s.trim()).filter(Boolean)
          : []
      };
      fetch('/api/chat/preferences/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(payload),
      })
        .then(resp => resp.json())
        .then(data => {
          applyTheme(data.tema);
          modal.classList.add('hidden');
        });
    });
  }

  if (saveKeyBtn && publicKeyInput) {
    saveKeyBtn.addEventListener('click', () => {
      const chave = publicKeyInput.value.trim();
      fetch('/api/chat/usuarios/chave-publica/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ chave_publica: chave }),
      })
        .then(resp => resp.json().then(data => ({ ok: resp.ok, data })))
        .then(result => {
          if (keyStatus) {
            if (result.ok) {
              keyStatus.textContent = (window.gettext ? gettext('Chave salva com sucesso.') : 'Chave salva com sucesso.');
              keyStatus.className = 'text-green-600 text-sm mt-1';
            } else {
              const msg = result.data && result.data.erro ? result.data.erro : (window.gettext ? gettext('Erro ao salvar chave.') : 'Erro ao salvar chave.');
              keyStatus.textContent = msg;
              keyStatus.className = 'text-red-600 text-sm mt-1';
            }
          }
        })
        .catch(() => {
          if (keyStatus) {
            keyStatus.textContent = (window.gettext ? gettext('Erro ao salvar chave.') : 'Erro ao salvar chave.');
            keyStatus.className = 'text-red-600 text-sm mt-1';
          }
        });
    });
  }

  loadPreferences();
  loadPublicKey();
});

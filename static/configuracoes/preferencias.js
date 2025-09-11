// Logic for preferencias toggle fields and theme/language updates

function initPreferencias() {
  const configEl = document.getElementById('preferencias-config');
  if (!configEl) return;

  const {
    chkEmail,
    chkWhats,
    chkPush,
    selEmail,
    selWhats,
    selPush,
    tema,
    idioma,
    updatedPreferences,
  } = configEl.dataset;

  const chkEmailEl = document.getElementById(chkEmail);
  const chkWhatsEl = document.getElementById(chkWhats);
  const chkPushEl = document.getElementById(chkPush);
  const selEmailEl = document.getElementById(selEmail);
  const selWhatsEl = document.getElementById(selWhats);
  const selPushEl = document.getElementById(selPush);
  const temaSelectEl = document.getElementById('id_tema');

  if (!chkEmailEl || !chkWhatsEl || !chkPushEl || !selEmailEl || !selWhatsEl || !selPushEl) {
    return;
  }

  function toggleFields() {
    selEmailEl.disabled = !chkEmailEl.checked;
    selEmailEl.classList.toggle('hidden', !chkEmailEl.checked);
    selWhatsEl.disabled = !chkWhatsEl.checked;
    selWhatsEl.classList.toggle('hidden', !chkWhatsEl.checked);
    selPushEl.disabled = !chkPushEl.checked;
    selPushEl.classList.toggle('hidden', !chkPushEl.checked);

    const freqEmail = chkEmailEl.checked ? selEmailEl.value : '';
    const freqWhats = chkWhatsEl.checked ? selWhatsEl.value : '';
    const freqPush = chkPushEl.checked ? selPushEl.value : '';

    const showDaily =
      freqEmail === 'diaria' ||
      freqWhats === 'diaria' ||
      freqPush === 'diaria';
    const showWeekly =
      freqEmail === 'semanal' ||
      freqWhats === 'semanal' ||
      freqPush === 'semanal';

    const hasHoraDiariaError = document.querySelector('#campo-hora-diaria [role="alert"]') !== null;
    const hasHoraSemanalError = document.querySelector('#campo-hora-semanal [role="alert"]') !== null;
    const hasDiaSemanalError = document.querySelector('#campo-dia-semanal [role="alert"]') !== null;

    document
      .getElementById('campo-hora-diaria')
      .classList.toggle('hidden', !(showDaily || hasHoraDiariaError));
    document
      .getElementById('campo-hora-semanal')
      .classList.toggle('hidden', !(showWeekly || hasHoraSemanalError));
    document
      .getElementById('campo-dia-semanal')
      .classList.toggle('hidden', !(showWeekly || hasDiaSemanalError));
  }

  selEmailEl.addEventListener('change', toggleFields);
  selWhatsEl.addEventListener('change', toggleFields);
  selPushEl.addEventListener('change', toggleFields);
  chkEmailEl.addEventListener('change', toggleFields);
  chkWhatsEl.addEventListener('change', toggleFields);
  chkPushEl.addEventListener('change', toggleFields);

  toggleFields();

  if (temaSelectEl) {
    const applyTheme = () => {
      const temaValue = temaSelectEl.value;
      localStorage.setItem('tema', temaValue);
      document.documentElement.classList.toggle('dark', temaValue === 'escuro');
    };
    temaSelectEl.addEventListener('change', applyTheme);
  }

  if (updatedPreferences === 'true') {
    const temaValue = tema;
    const idiomaValue = idioma;
    localStorage.setItem('tema', temaValue);
    document.documentElement.classList.toggle('dark', temaValue === 'escuro');
    localStorage.setItem('idioma', idiomaValue);
    document.cookie = `django_language=${idiomaValue};path=/`;
    document.documentElement.setAttribute('lang', idiomaValue);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPreferencias);
} else {
  initPreferencias();
}


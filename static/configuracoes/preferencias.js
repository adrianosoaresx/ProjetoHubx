// Logic for preferencias toggle fields and theme/language updates

const PREFERENCIAS_MESSAGE_TARGETS = {
  email: 'msg-email',
  whatsapp: 'msg-whatsapp',
  push: 'msg-push',
};

function handlePreferenciasAfterRequest(event) {
  const detail = event.detail;
  if (!detail) return;

  const responseDetail = detail.xhr?.responseJSON?.detail;
  if (!responseDetail) return;

  const parameters =
    detail.requestConfig?.parameters || detail.parameters || {};
  const canal = parameters?.canal;
  if (!canal) return;

  const targetId = PREFERENCIAS_MESSAGE_TARGETS[canal];
  if (!targetId) return;

  const messageEl = document.getElementById(targetId);
  if (messageEl) {
    messageEl.innerText = responseDetail;
  }
}

function handlePreferenciasAfterSwap(event) {
  const target = event.detail?.target ?? event.target;
  if (target?.id === 'content') {
    initPreferencias();
  }
}

function setupPreferenciasAfterSwapListener() {
  if (!document.body) return;
  document.body.removeEventListener('htmx:afterSwap', handlePreferenciasAfterSwap);
  document.body.addEventListener('htmx:afterSwap', handlePreferenciasAfterSwap);
}

function initPreferencias() {
  const chkEmailId = document.getElementById('chk_email_id');
  const chkWhatsId = document.getElementById('chk_whats_id');
  const chkPushId = document.getElementById('chk_push_id');
  const selEmailId = document.getElementById('sel_email_id');
  const selWhatsId = document.getElementById('sel_whats_id');
  const selPushId = document.getElementById('sel_push_id');
  const temaInput = document.getElementById('tema_atual');
  const idiomaInput = document.getElementById('idioma_atual');
  const updatedPreferencesInput = document.getElementById('updated_preferences');

  if (
    !chkEmailId ||
    !chkWhatsId ||
    !chkPushId ||
    !selEmailId ||
    !selWhatsId ||
    !selPushId
  ) {
    return;
  }

  const chkEmailEl = document.getElementById(chkEmailId.value);
  const chkWhatsEl = document.getElementById(chkWhatsId.value);
  const chkPushEl = document.getElementById(chkPushId.value);
  const selEmailEl = document.getElementById(selEmailId.value);
  const selWhatsEl = document.getElementById(selWhatsId.value);
  const selPushEl = document.getElementById(selPushId.value);
  const temaSelectEl = document.getElementById('id_tema');

  if (
    !chkEmailEl ||
    !chkWhatsEl ||
    !chkPushEl ||
    !selEmailEl ||
    !selWhatsEl ||
    !selPushEl
  ) {
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

  // Ensure multiple calls to initPreferencias do not stack listeners
  selEmailEl.onchange = toggleFields;
  selWhatsEl.onchange = toggleFields;
  selPushEl.onchange = toggleFields;
  chkEmailEl.onchange = toggleFields;
  chkWhatsEl.onchange = toggleFields;
  chkPushEl.onchange = toggleFields;

  toggleFields();

  if (temaSelectEl) {
    const applyTheme = () => {
      const temaValue = temaSelectEl.value;
      localStorage.setItem('tema', temaValue);
      document.documentElement.classList.toggle('dark', temaValue === 'escuro');
    };
    temaSelectEl.onchange = applyTheme;
  }

  if (updatedPreferencesInput?.value === 'true') {
    const temaValue = temaInput?.value;
    const idiomaValue = idiomaInput?.value;
    if (temaValue) {
      localStorage.setItem('tema', temaValue);
      document.documentElement.classList.toggle('dark', temaValue === 'escuro');
    }
    if (idiomaValue) {
      localStorage.setItem('idioma', idiomaValue);
      document.cookie = `django_language=${idiomaValue};path=/`;
      document.documentElement.setAttribute('lang', idiomaValue);
    }
  }

  if (document.body) {
    document.body.removeEventListener('htmx:afterRequest', handlePreferenciasAfterRequest);
    document.body.addEventListener('htmx:afterRequest', handlePreferenciasAfterRequest);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initPreferencias();
    setupPreferenciasAfterSwapListener();
  });
} else {
  initPreferencias();
  setupPreferenciasAfterSwapListener();
}


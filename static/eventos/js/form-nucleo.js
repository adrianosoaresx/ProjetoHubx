document.addEventListener('DOMContentLoaded', () => {
  const publicoAlvoSelect = document.getElementById('id_publico_alvo');
  const nucleoInput = document.getElementById('id_nucleo');
  const nucleoFieldWrapper = document.getElementById('nucleo-field-container');

  const toggleNucleoField = () => {
    if (!publicoAlvoSelect || !nucleoInput || !nucleoFieldWrapper) {
      return;
    }

    const isLocked =
      nucleoInput.type === 'hidden' ||
      nucleoFieldWrapper.dataset.nucleoLocked === 'true';

    if (isLocked) {
      nucleoFieldWrapper.classList.add('hidden');
      return;
    }

    if (publicoAlvoSelect.value === '1') {
      nucleoFieldWrapper.classList.remove('hidden');
    } else {
      nucleoFieldWrapper.classList.add('hidden');
      nucleoInput.value = '';
    }
  };

  toggleNucleoField();

  if (publicoAlvoSelect) {
    publicoAlvoSelect.addEventListener('change', toggleNucleoField);
  }
});

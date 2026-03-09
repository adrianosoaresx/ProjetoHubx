  (function () {
    const modalContainer = document.getElementById('modal');

    if (!modalContainer || modalContainer.dataset.nucleacaoCloseBound === 'true') {
      return;
    }

    modalContainer.dataset.nucleacaoCloseBound = 'true';

    document.body.addEventListener('nucleacao:close-modal', function () {
      const modal = document.getElementById('modal');
      if (modal) {
        modal.innerHTML = '';
      }
    });
  })();

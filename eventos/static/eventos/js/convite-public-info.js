    (function () {
      const copyButton = document.querySelector('[data-copy-link]');
      if (!copyButton || !navigator.clipboard) {
        return;
      }

      const originalText = copyButton.textContent.trim();
      const successText = copyButton.dataset.copySuccess || originalText;

      copyButton.addEventListener('click', async () => {
        const link = copyButton.getAttribute('data-copy-link');
        try {
          await navigator.clipboard.writeText(link);
          copyButton.textContent = successText;
          copyButton.disabled = true;
          setTimeout(() => {
            copyButton.textContent = originalText;
            copyButton.disabled = false;
          }, 1500);
        } catch (err) {
          console.error('Erro ao copiar link do convite', err);
        }
      });
    })();
  

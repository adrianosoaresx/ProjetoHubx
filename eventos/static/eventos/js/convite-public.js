    (function () {
      const copyButtons = document.querySelectorAll('[data-copy-link]');
      if (!copyButtons.length) {
        return;
      }

      async function copyText(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text);
          return;
        }

        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'absolute';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);

        try {
          textarea.select();
          const copied = document.execCommand('copy');
          if (!copied) {
            throw new Error('document.execCommand("copy") retornou false');
          }
        } finally {
          document.body.removeChild(textarea);
        }
      }

      copyButtons.forEach((copyButton) => {
        const originalText = copyButton.textContent.trim();
        const successText = copyButton.dataset.copySuccess || originalText;

        copyButton.addEventListener('click', async () => {
          const link = copyButton.getAttribute('data-copy-link');
          try {
            await copyText(link);
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
      });
    })();
  

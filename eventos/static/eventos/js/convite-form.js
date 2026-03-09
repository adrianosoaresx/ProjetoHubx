    document.addEventListener('DOMContentLoaded', () => {
      const input = document.querySelector('[data-convite-image-input]');
      const previewContainer = document.getElementById('convite-image-preview');
      const previewImage = previewContainer ? previewContainer.querySelector('img') : null;

      if (!input || !previewContainer || !previewImage) return;

      input.addEventListener('change', (event) => {
        const [file] = event.target.files || [];
        if (!file) {
          previewImage.classList.add('hidden');
          previewImage.removeAttribute('src');
          return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
          previewImage.src = e.target.result;
          previewImage.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
      });
    });
  

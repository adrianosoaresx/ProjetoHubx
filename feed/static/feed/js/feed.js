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
    postForm.addEventListener("submit", (e) => {
      const content = textarea ? textarea.value.trim() : "";
      const hasFile = fileInput && fileInput.files.length > 0;

      if (content.length === 0 && !hasFile) {
        e.preventDefault();
        const msg = window.gettext
          ? gettext(
              "Por favor, escreva algo ou selecione um arquivo antes de publicar.",
            )
          : "Por favor, escreva algo ou selecione um arquivo antes de publicar.";
        alert(msg);
        if (textarea) textarea.focus();
        return false;
      }

      if (content.length > 500) {
        e.preventDefault();
        const msg = window.gettext
          ? gettext("O conteúdo deve ter no máximo 500 caracteres.")
          : "O conteúdo deve ter no máximo 500 caracteres.";
        alert(msg);
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

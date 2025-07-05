// Feed JavaScript - Funcionalidades essenciais
document.addEventListener("DOMContentLoaded", () => {
  // Contador de caracteres para textarea
  const textarea = document.querySelector('textarea[name="conteudo"]')
  const charCounter = document.getElementById("char-count")

  if (textarea && charCounter) {
    // Função para atualizar contador
    function updateCharCounter() {
      const currentLength = textarea.value.length
      const maxLength = 500

      charCounter.textContent = currentLength

      // Mudar cor baseado no limite
      if (currentLength > maxLength * 0.9) {
        charCounter.style.color = "var(--danger-color)"
      } else if (currentLength > maxLength * 0.7) {
        charCounter.style.color = "var(--warning-color)"
      } else {
        charCounter.style.color = "var(--text-muted)"
      }
    }

    // Atualizar contador inicial e em tempo real
    updateCharCounter()
    textarea.addEventListener("input", updateCharCounter)
  }

  // Preview do nome do arquivo selecionado
  const fileInput = document.querySelector('input[type="file"]')
  const fileText = document.querySelector(".file-text")

  if (fileInput && fileText) {
    const originalText = fileText.textContent

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0]

      if (file) {
        // Verificar se é uma imagem
        if (file.type.startsWith("image/")) {
          fileText.textContent = `Selecionado: ${file.name}`
          fileText.style.color = "var(--success-color)"
        } else {
          alert("Por favor, selecione apenas arquivos de imagem.")
          fileInput.value = ""
          fileText.textContent = originalText
          fileText.style.color = "var(--text-secondary)"
        }
      } else {
        fileText.textContent = originalText
        fileText.style.color = "var(--text-secondary)"
      }
    })
  }

  // Validação básica do formulário
  const postForm = document.querySelector(".post-form")

  if (postForm) {
    postForm.addEventListener("submit", (e) => {
      const content = textarea.value.trim()

      if (content.length === 0) {
        e.preventDefault()
        alert("Por favor, escreva algo antes de publicar.")
        textarea.focus()
        return false
      }

      if (content.length > 500) {
        e.preventDefault()
        alert("O conteúdo deve ter no máximo 500 caracteres.")
        textarea.focus()
        return false
      }
    })
  }

  // Auto-resize do textarea
  if (textarea) {
    textarea.addEventListener("input", function () {
      this.style.height = "auto"
      this.style.height = Math.min(this.scrollHeight, 300) + "px"
    })
  }
})

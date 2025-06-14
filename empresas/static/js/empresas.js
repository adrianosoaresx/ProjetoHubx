// JavaScript para Formulários de Empresa - HubX
// Este arquivo está vazio por enquanto, mas pode ser usado para:
// - Validações de formulário em tempo real
// - Lógica de upload de imagem (pré-visualização de logo)
// - Interações dinâmicas com campos do formulário
// - Integração com APIs de CEP, etc.

document.addEventListener("DOMContentLoaded", () => {
  // Exemplo: Adicionar uma classe 'is-invalid' para campos com erros
  const form = document.querySelector(".empresa-form-container form")
  if (form) {
    form.querySelectorAll("p").forEach((p) => {
      if (p.querySelector(".errorlist")) {
        const input = p.querySelector("input, select, textarea")
        if (input) {
          input.classList.add("is-invalid")
        }
      }
    })
  }
})

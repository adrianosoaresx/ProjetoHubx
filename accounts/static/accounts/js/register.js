// Registro Multi-step JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

    // Initialize Success Page Effects
    if (document.querySelector(".success-container")) {
        initSuccessPage()
    }

    // Initialize Form Validation
    initFormValidation()

    // Forms now submit directly to the server

    // Initialize Photo Upload if on photo page
    if (document.getElementById("fotoForm")) {
        initPhotoUpload()
    }

    // Initialize Password Strength if on password page
    if (document.getElementById("senha")) {
        initPasswordStrength()
    }

    // Session persistence handled server-side
})

// Matrix Code Rain Effect
function initMatrixRain() {
    const matrixContainer = document.getElementById("matrixCode")
    if (!matrixContainer) return

    const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$+-*/=%\"'#&_(),.;:?!\\|{}<>[]^~"
    const columnCount = 15

    for (let i = 0; i < columnCount; i++) {
        const column = document.createElement("div")
        column.className = "code-column"

        // Random position and speed
        column.style.left = `${Math.random() * 100}%`
        column.style.animationDuration = `${Math.random() * 15 + 8}s`
        column.style.animationDelay = `${Math.random() * 5}s`

        // Generate random characters
        const charCount = Math.floor(Math.random() * 25) + 15
        for (let j = 0; j < charCount; j++) {
            const char = document.createElement("div")
            char.textContent = characters.charAt(Math.floor(Math.random() * characters.length))
            char.style.opacity = Math.random() * 0.8 + 0.2
            column.appendChild(char)
        }

        matrixContainer.appendChild(column)
    }
}

// Form Validation
function initFormValidation() {
    const currentForm = document.querySelector(".registro-form")
    if (!currentForm) return

    const formId = currentForm.id

    switch (formId) {
        case "tokenForm":
            initTokenValidation()
            break
        case "nomeForm":
            initNomeValidation()
            break
        case "emailForm":
            initEmailValidation()
            break
        case "usuarioForm":
            initUsuarioValidation()
            break
        case "senhaForm":
            initSenhaValidation()
            break
        case "fotoForm":
            // Photo validation is handled in initPhotoUpload
            break
        case "termosForm":
            initTermosValidation()
            break
    }
}

// Token Validation
function initTokenValidation() {
    const tokenInput = document.getElementById("token")
    const tokenValidation = document.getElementById("token_validation")

    if (!tokenInput || !tokenValidation) return

    tokenInput.addEventListener("blur", validateToken)
    tokenInput.addEventListener("input", () => {
        clearFieldValidation(tokenInput, tokenValidation)
    })
}

function validateToken() {
    const tokenInput = document.getElementById("token")
    const tokenValidation = document.getElementById("token_validation")
    const token = tokenInput.value.trim()

    if (token.length === 0) {
        showValidation(tokenInput, tokenValidation, "Token é obrigatório", false)
        return false
    }

    if (token.length < 6) {
        showValidation(tokenInput, tokenValidation, "Token deve ter pelo menos 6 caracteres", false)
        return false
    }

    // Simulate token validation with backend
    showValidation(tokenInput, tokenValidation, "Verificando token...", null)

    // Simulate API call
    return new Promise((resolve) => {
        setTimeout(() => {
            // For demo purposes, we'll consider tokens starting with "HUBX" as valid
            if (token.toUpperCase().startsWith("HUBX")) {
                showValidation(tokenInput, tokenValidation, "Token válido", true)
                resolve(true)
            } else {
                showValidation(tokenInput, tokenValidation, "Token inválido ou expirado", false)
                resolve(false)
            }
        }, 1000)
    })
}

// Nome Validation
function initNomeValidation() {
    const nomeInput = document.getElementById("nome")
    const nomeValidation = document.getElementById("nome_validation")

    if (!nomeInput || !nomeValidation) return

    nomeInput.addEventListener("blur", validateNome)
    nomeInput.addEventListener("input", () => {
        clearFieldValidation(nomeInput, nomeValidation)
    })
}

function validateNome() {
    const nomeInput = document.getElementById("nome")
    const nomeValidation = document.getElementById("nome_validation")
    const nome = nomeInput.value.trim()

    if (nome.length === 0) {
        showValidation(nomeInput, nomeValidation, "Nome é obrigatório", false)
        return false
    }

    if (nome.length < 3) {
        showValidation(nomeInput, nomeValidation, "Nome deve ter pelo menos 3 caracteres", false)
        return false
    }

    if (!/^[a-zA-ZÀ-ÿ\s]+$/.test(nome)) {
        showValidation(nomeInput, nomeValidation, "Nome deve conter apenas letras", false)
        return false
    }

    if (!nome.includes(" ")) {
        showValidation(nomeInput, nomeValidation, "Digite seu nome completo", false)
        return false
    }

    showValidation(nomeInput, nomeValidation, "Nome válido", true)
    return true
}

// Email Validation
function initEmailValidation() {
    const emailInput = document.getElementById("email")
    const emailValidation = document.getElementById("email_validation")

    if (!emailInput || !emailValidation) return

    emailInput.addEventListener("blur", validateEmail)
    emailInput.addEventListener("input", () => {
        clearFieldValidation(emailInput, emailValidation)
    })
}

function validateEmail() {
    const emailInput = document.getElementById("email")
    const emailValidation = document.getElementById("email_validation")
    const email = emailInput.value.trim()

    if (email.length === 0) {
        showValidation(emailInput, emailValidation, "Email é obrigatório", false)
        return false
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
        showValidation(emailInput, emailValidation, "Digite um email válido", false)
        return false
    }

    // Simulate email validation with backend
    showValidation(emailInput, emailValidation, "Verificando email...", null)

    // Simulate API call
    return new Promise((resolve) => {
        setTimeout(() => {
            // For demo purposes, we'll consider emails not ending with "test.com" as valid
            if (!email.endsWith("test.com")) {
                showValidation(emailInput, emailValidation, "Email válido", true)
                resolve(true)
            } else {
                showValidation(emailInput, emailValidation, "Este email já está em uso", false)
                resolve(false)
            }
        }, 1000)
    })
}

// Usuario Validation
function initUsuarioValidation() {
    const usuarioInput = document.getElementById("usuario")
    const usuarioValidation = document.getElementById("usuario_validation")

    if (!usuarioInput || !usuarioValidation) return

    usuarioInput.addEventListener("blur", validateUsuario)
    usuarioInput.addEventListener("input", () => {
        clearFieldValidation(usuarioInput, usuarioValidation)
    })
}

function validateUsuario() {
    const usuarioInput = document.getElementById("usuario")
    const usuarioValidation = document.getElementById("usuario_validation")
    const usuario = usuarioInput.value.trim()

    if (usuario.length === 0) {
        showValidation(usuarioInput, usuarioValidation, "Nome de usuário é obrigatório", false)
        return false
    }

    if (usuario.length < 3) {
        showValidation(usuarioInput, usuarioValidation, "Nome de usuário deve ter pelo menos 3 caracteres", false)
        return false
    }

    if (!/^[a-zA-Z0-9_]+$/.test(usuario)) {
        showValidation(usuarioInput, usuarioValidation, "Use apenas letras, números e underscore (_)", false)
        return false
    }

    // Simulate username validation with backend
    showValidation(usuarioInput, usuarioValidation, "Verificando disponibilidade...", null)

    // Simulate API call
    return new Promise((resolve) => {
        setTimeout(() => {
            // For demo purposes, we'll consider usernames not starting with "admin" as valid
            if (!usuario.toLowerCase().startsWith("admin")) {
                showValidation(usuarioInput, usuarioValidation, "Nome de usuário disponível", true)
                resolve(true)
            } else {
                showValidation(usuarioInput, usuarioValidation, "Este nome de usuário já está em uso", false)
                resolve(false)
            }
        }, 1000)
    })
}

// Senha Validation
function initSenhaValidation() {
    const senhaInput = document.getElementById("senha")
    const confirmarSenhaInput = document.getElementById("confirmar_senha")
    const senhaValidation = document.getElementById("senha_validation")
    const confirmarSenhaValidation = document.getElementById("confirmar_senha_validation")

    if (!senhaInput || !confirmarSenhaInput) return

    senhaInput.addEventListener("blur", validateSenha)
    senhaInput.addEventListener("input", () => {
        clearFieldValidation(senhaInput, senhaValidation)

        // Re-validate password confirmation if it has a value
        if (confirmarSenhaInput.value.trim().length > 0) {
            validateConfirmarSenha()
        }
    })

    confirmarSenhaInput.addEventListener("blur", validateConfirmarSenha)
    confirmarSenhaInput.addEventListener("input", () => {
        clearFieldValidation(confirmarSenhaInput, confirmarSenhaValidation)
    })
}

function validateSenha() {
    const senhaInput = document.getElementById("senha")
    const senhaValidation = document.getElementById("senha_validation")
    const senha = senhaInput.value

    if (senha.length === 0) {
        showValidation(senhaInput, senhaValidation, "Senha é obrigatória", false)
        return false
    }

    if (senha.length < 8) {
        showValidation(senhaInput, senhaValidation, "Senha deve ter pelo menos 8 caracteres", false)
        return false
    }

    const hasUpper = /[A-Z]/.test(senha)
    const hasLower = /[a-z]/.test(senha)
    const hasNumber = /\d/.test(senha)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(senha)

    const score = [hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length

    if (score < 3) {
        showValidation(
            senhaInput,
            senhaValidation,
            "Senha deve conter pelo menos 3 dos seguintes: maiúsculas, minúsculas, números e caracteres especiais",
            false,
        )
        return false
    }

    showValidation(senhaInput, senhaValidation, "Senha válida", true)
    return true
}

function validateConfirmarSenha() {
    const senhaInput = document.getElementById("senha")
    const confirmarSenhaInput = document.getElementById("confirmar_senha")
    const confirmarSenhaValidation = document.getElementById("confirmar_senha_validation")

    const senha = senhaInput.value
    const confirmarSenha = confirmarSenhaInput.value

    if (confirmarSenha.length === 0) {
        showValidation(confirmarSenhaInput, confirmarSenhaValidation, "Confirmação de senha é obrigatória", false)
        return false
    }

    if (senha !== confirmarSenha) {
        showValidation(confirmarSenhaInput, confirmarSenhaValidation, "As senhas não coincidem", false)
        return false
    }

    showValidation(confirmarSenhaInput, confirmarSenhaValidation, "Senhas coincidem", true)
    return true
}

// Termos Validation
function initTermosValidation() {
    const termosCheckbox = document.getElementById("aceitar_termos")
    const submitButton = document.getElementById("submitButton")

    if (!termosCheckbox || !submitButton) return

    termosCheckbox.addEventListener("change", () => {
        submitButton.disabled = !termosCheckbox.checked

        if (termosCheckbox.checked) {
            submitButton.classList.remove("disabled")
        } else {
            submitButton.classList.add("disabled")
        }
    })

    // Initialize button state
    submitButton.disabled = !termosCheckbox.checked
    if (!termosCheckbox.checked) {
        submitButton.classList.add("disabled")
    }
}

// Password Strength
function initPasswordStrength() {
    const senhaInput = document.getElementById("senha")
    const strengthFill = document.getElementById("strengthFill")
    const strengthText = document.getElementById("strengthText")

    if (!senhaInput || !strengthFill || !strengthText) return

    senhaInput.addEventListener("input", function() {
        const senha = this.value
        updatePasswordStrength(senha, strengthFill, strengthText)
    })
}

function updatePasswordStrength(password, fillElement, textElement) {
    if (password.length === 0) {
        fillElement.style.width = "0%"
        textElement.textContent = "Digite uma senha"
        fillElement.style.background = "var(--error-color)"
        return
    }

    const hasLength = password.length >= 8
    const hasUpper = /[A-Z]/.test(password)
    const hasLower = /[a-z]/.test(password)
    const hasNumber = /\d/.test(password)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password)

    const criteria = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial]
    const score = criteria.filter(Boolean).length

    let strength = {
        width: 0,
        text: "Muito fraca",
        color: "var(--error-color)",
    }

    switch (score) {
        case 0:
        case 1:
            strength = { width: 20, text: "Muito fraca", color: "#ff4757" }
            break
        case 2:
            strength = { width: 40, text: "Fraca", color: "#ff6b7a" }
            break
        case 3:
            strength = { width: 60, text: "Média", color: "#ffa502" }
            break
        case 4:
            strength = { width: 80, text: "Forte", color: "#2ed573" }
            break
        case 5:
            strength = { width: 100, text: "Muito forte", color: "var(--matrix-green)" }
            break
    }

    fillElement.style.width = `${strength.width}%`
    fillElement.style.background = strength.color
    textElement.textContent = strength.text
}

// Photo Upload
function initPhotoUpload() {
    const fotoInput = document.getElementById("foto")
    const fotoPreview = document.getElementById("fotoPreview")
    const removeButton = document.getElementById("removePhoto")
    const fotoValidation = document.getElementById("foto_validation")

    if (!fotoInput || !fotoPreview || !removeButton) return

    fotoInput.addEventListener("change", handlePhotoUpload)
    removeButton.addEventListener("click", removePhoto)
}

function handlePhotoUpload(event) {
    const file = event.target.files[0]
    const fotoPreview = document.getElementById("fotoPreview")
    const removeButton = document.getElementById("removePhoto")
    const fotoValidation = document.getElementById("foto_validation")

    if (!file) return

    // Validate file type
    const allowedTypes = ["image/jpeg", "image/jpg", "image/png"]
    if (!allowedTypes.includes(file.type)) {
        showValidation(null, fotoValidation, "Formato não suportado. Use JPG ou PNG", false)
        event.target.value = ""
        return
    }

    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024 // 5MB in bytes
    if (file.size > maxSize) {
        showValidation(null, fotoValidation, "Arquivo muito grande. Máximo 5MB", false)
        event.target.value = ""
        return
    }

    // Create preview
    const reader = new FileReader()
    reader.onload = (e) => {
        fotoPreview.innerHTML = `<img src="${e.target.result}" alt="Preview da foto">`
        removeButton.disabled = false
        showValidation(null, fotoValidation, "Foto carregada com sucesso", true)

        // Store photo data
        storeFormData("foto", e.target.result)
    }
    reader.readAsDataURL(file)
}

function removePhoto() {
    const fotoInput = document.getElementById("foto")
    const fotoPreview = document.getElementById("fotoPreview")
    const removeButton = document.getElementById("removePhoto")
    const fotoValidation = document.getElementById("foto_validation")

    fotoInput.value = ""
    fotoPreview.innerHTML = `
    <div class="foto-placeholder">
      <span class="foto-icon">👤</span>
    </div>
  `
    removeButton.disabled = true
    fotoValidation.textContent = ""
    fotoValidation.classList.remove("valid", "invalid")

    // Remove from storage
    removeFormData("foto")
}

// Form Submission
function initFormSubmission() {
    const currentForm = document.querySelector(".registro-form")
    if (!currentForm) return

    currentForm.addEventListener("submit", handleFormSubmission)
}

async function handleFormSubmission(event) {
    const form = event.target
    const formId = form.id

    if (formId === "termosForm") {
        // Allow Django to handle submission of the final step
        return
    }

    event.preventDefault()
    const submitButton = document.getElementById("submitButton")
    const buttonText = submitButton.querySelector(".button-text")
    const buttonLoader = document.getElementById("buttonLoader")

    // Show loading state
    submitButton.classList.add("loading")
    submitButton.disabled = true

    let isValid = false

    try {
        // Validate current form
        switch (formId) {
            case "tokenForm":
                isValid = await validateToken()
                break
            case "nomeForm":
                isValid = validateNome()
                break
            case "emailForm":
                isValid = await validateEmail()
                break
            case "usuarioForm":
                isValid = await validateUsuario()
                break
            case "senhaForm":
                isValid = validateSenha() && validateConfirmarSenha()
                break
            case "fotoForm":
                isValid = true // Photo is optional
                break
            case "termosForm":
                isValid = document.getElementById("aceitar_termos").checked
                break
            default:
                isValid = true
        }

        // Simulate processing time
        await new Promise((resolve) => setTimeout(resolve, 1000))

        if (isValid) {
            // Store form data
            storeCurrentFormData(form)

            // Navigate to next step
            const nextStep = form.dataset.nextStep
            if (nextStep) {
                if (formId === "termosForm") {
                    // Final step - submit all data
                    await submitRegistration()
                } else {
                    window.location.href = nextStep
                }
            }
        } else {
            // Show error message
            if (formId === "tokenForm") {
                const tokenValidation = document.getElementById("token_validation")
                showValidation(null, tokenValidation, "Token é obrigatório para continuar", false)
            }
        }
    } catch (error) {
        console.error("Erro na validação:", error)
    } finally {
        // Hide loading state
        submitButton.classList.remove("loading")
        submitButton.disabled = false
    }
}

// Form Data Storage
function storeCurrentFormData(form) {
    const formData = new FormData(form)

    for (const [key, value] of formData.entries()) {
        storeFormData(key, value)
    }
}

function storeFormData(key, value) {
    try {
        const registroData = JSON.parse(sessionStorage.getItem("registroData") || "{}")
        registroData[key] = value
        sessionStorage.setItem("registroData", JSON.stringify(registroData))
    } catch (error) {
        console.error("Erro ao armazenar dados:", error)
    }
}

function removeFormData(key) {
    try {
        const registroData = JSON.parse(sessionStorage.getItem("registroData") || "{}")
        delete registroData[key]
        sessionStorage.setItem("registroData", JSON.stringify(registroData))
    } catch (error) {
        console.error("Erro ao remover dados:", error)
    }
}

function loadFormData() {
    try {
        const registroData = JSON.parse(sessionStorage.getItem("registroData") || "{}")

        // Fill form fields with stored data
        Object.keys(registroData).forEach((key) => {
            const field = document.getElementById(key)
            if (field && field.type !== "file") {
                field.value = registroData[key]
            }
        })
    } catch (error) {
        console.error("Erro ao carregar dados:", error)
    }
}

// Final Registration Submission
async function submitRegistration() {
    try {
        const registroData = JSON.parse(sessionStorage.getItem("registroData") || "{}")

        // Here you would send the data to your backend
        console.log("Dados do registro:", registroData)

        // Simulate API call
        const response = await fetch("/api/registro/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(registroData),
        })

        if (response.ok) {
            // Clear stored data
            sessionStorage.removeItem("registroData")

            // Redirect to success page
            window.location.href = "/registro/sucesso/"
        } else {
            throw new Error("Erro no servidor")
        }
    } catch (error) {
        console.error("Erro ao finalizar registro:", error)
        alert("Erro ao finalizar o cadastro. Tente novamente.")
    }
}

// Success Page Animations
function initSuccessPage() {
    createConfetti()

    const card = document.querySelector(".success-card")
    if (card) {
        card.style.opacity = "0"
        card.style.transform = "translateY(30px)"

        setTimeout(() => {
            card.style.transition = "all 0.8s ease"
            card.style.opacity = "1"
            card.style.transform = "translateY(0)"
        }, 100)
    }
}

function createConfetti() {
    const container = document.getElementById("confettiContainer")
    if (!container) return

    const colors = ["#00ff41", "#39ff14", "#00bf32", "#ffffff"]
    const confettiCount = 100

    for (let i = 0; i < confettiCount; i++) {
        const confetti = document.createElement("div")
        confetti.className = "confetti"
        confetti.style.left = `${Math.random() * 100}%`
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)]
        const size = Math.random() * 8 + 5
        confetti.style.width = `${size}px`
        confetti.style.height = `${size}px`
        confetti.style.transform = `rotate(${Math.random() * 360}deg)`
        if (Math.random() > 0.5) {
            confetti.style.borderRadius = "50%"
        } else {
            confetti.style.borderRadius = "0"
        }
        const duration = Math.random() * 3 + 2
        confetti.style.animationDuration = `${duration}s`
        confetti.style.animationDelay = `${Math.random() * 5}s`
        container.appendChild(confetti)
    }
}

// Utility Functions
function showValidation(field, validationElement, message, isValid) {
    if (validationElement) {
        validationElement.textContent = message

        // Remove previous classes
        validationElement.classList.remove("valid", "invalid")

        if (isValid === true) {
            validationElement.classList.add("valid")
            if (field) field.classList.add("valid")
        } else if (isValid === false) {
            validationElement.classList.add("invalid")
            if (field) field.classList.add("invalid")
        }
    }

    if (field) {
        field.classList.remove("valid", "invalid")
        if (isValid === true) {
            field.classList.add("valid")
        } else if (isValid === false) {
            field.classList.add("invalid")
        }
    }
}

function clearFieldValidation(field, validationElement) {
    if (field) {
        field.classList.remove("valid", "invalid")
    }
    if (validationElement) {
        validationElement.classList.remove("valid", "invalid")
        validationElement.textContent = ""
    }
}

function getCsrfToken() {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
    return csrfToken ? csrfToken.value : ""
}

// Keyboard Navigation
document.addEventListener("keydown", (event) => {
    // Allow Enter to submit forms
    if (event.key === "Enter" && event.target.tagName === "INPUT") {
        const form = event.target.closest("form")
        if (form) {
            const submitButton = form.querySelector('button[type="submit"]')
            if (submitButton && !submitButton.disabled) {
                submitButton.click()
            }
        }
    }
})


// Código JavaScript existente mantido - adicionando apenas funcionalidades para CPF

// CPF Mask and Validation Functions
function applyCpfMask(value) {
  // Remove all non-numeric characters
  value = value.replace(/\D/g, "")

  // Apply CPF mask: 000.000.000-00
  if (value.length <= 11) {
    value = value.replace(/(\d{3})(\d)/, "$1.$2")
    value = value.replace(/(\d{3})(\d)/, "$1.$2")
    value = value.replace(/(\d{3})(\d{1,2})$/, "$1-$2")
  }

  return value
}

function validateCpf(cpf) {
  // Remove mask
  cpf = cpf.replace(/[^\d]/g, "")

  // Check if CPF has 11 digits
  if (cpf.length !== 11) {
    return false
  }

  // Check if all digits are the same
  if (/^(\d)\1{10}$/.test(cpf)) {
    return false
  }

  // Validate CPF algorithm
  let sum = 0
  let remainder

  // Validate first digit
  for (let i = 1; i <= 9; i++) {
    sum += Number.parseInt(cpf.substring(i - 1, i)) * (11 - i)
  }
  remainder = (sum * 10) % 11
  if (remainder === 10 || remainder === 11) remainder = 0
  if (remainder !== Number.parseInt(cpf.substring(9, 10))) return false

  // Validate second digit
  sum = 0
  for (let i = 1; i <= 10; i++) {
    sum += Number.parseInt(cpf.substring(i - 1, i)) * (12 - i)
  }
  remainder = (sum * 10) % 11
  if (remainder === 10 || remainder === 11) remainder = 0
  if (remainder !== Number.parseInt(cpf.substring(10, 11))) return false

  return true
}

function showCpfValidation(input, isValid, message) {
  const validation = document.getElementById("cpf_validation")
  const submitButton = document.getElementById("submitButton")

  // Remove previous classes
  input.classList.remove("cpf-valid", "cpf-invalid", "cpf-validating")
  validation.classList.remove("cpf-success", "cpf-error")

  if (isValid === null) {
    // Validating state
    input.classList.add("cpf-validating")
    validation.textContent = "Validando CPF..."
    submitButton.disabled = true
  } else if (isValid) {
    // Valid state
    input.classList.add("cpf-valid")
    validation.classList.add("cpf-success")
    validation.textContent = message || "CPF válido"
    submitButton.disabled = false
  } else {
    // Invalid state
    input.classList.add("cpf-invalid")
    validation.classList.add("cpf-error")
    validation.textContent = message || "CPF inválido"
    submitButton.disabled = true
  }
}

// Initialize CPF form when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  const cpfForm = document.getElementById("cpfForm")
  const cpfInput = document.getElementById("cpf")

  if (cpfForm && cpfInput) {
    let validationTimeout

    // Apply mask on input
    cpfInput.addEventListener("input", (e) => {
      const cursorPosition = e.target.selectionStart
      const oldValue = e.target.value
      const newValue = applyCpfMask(e.target.value)

      e.target.value = newValue

      // Maintain cursor position
      const newCursorPosition = cursorPosition + (newValue.length - oldValue.length)
      e.target.setSelectionRange(newCursorPosition, newCursorPosition)

      // Clear previous validation timeout
      clearTimeout(validationTimeout)

      // Show validating state
      if (newValue.length > 0) {
        showCpfValidation(cpfInput, null)

        // Validate after user stops typing (500ms delay)
        validationTimeout = setTimeout(() => {
          const isValid = validateCpf(newValue)
          if (newValue.replace(/\D/g, "").length === 11) {
            showCpfValidation(cpfInput, isValid, isValid ? "CPF válido" : "CPF inválido")
          } else {
            showCpfValidation(cpfInput, false, "CPF deve ter 11 dígitos")
          }
        }, 500)
      } else {
        // Clear validation when input is empty
        document.getElementById("cpf_validation").textContent = ""
        cpfInput.classList.remove("cpf-valid", "cpf-invalid", "cpf-validating")
        document.getElementById("submitButton").disabled = false
      }
    })

    // Validate on form submit
    cpfForm.addEventListener("submit", (e) => {
      const cpfValue = cpfInput.value

      if (!cpfValue || !validateCpf(cpfValue)) {
        e.preventDefault()
        showCpfValidation(cpfInput, false, "Por favor, insira um CPF válido")
        cpfInput.focus()
        return false
      }

      // Show loading state
      const submitButton = document.getElementById("submitButton")
      const buttonText = submitButton.querySelector(".button-text")
      const buttonLoader = document.getElementById("buttonLoader")

      submitButton.disabled = true
      buttonText.style.opacity = "0"
      buttonLoader.style.display = "inline-block"
    })

    // Allow only numbers and formatting characters
    cpfInput.addEventListener("keypress", (e) => {
      const char = String.fromCharCode(e.which)
      if (!/[\d.-]/.test(char) && !e.ctrlKey && !e.metaKey && e.which !== 8 && e.which !== 9) {
        e.preventDefault()
      }
    })

    // Prevent paste of invalid characters
    cpfInput.addEventListener("paste", (e) => {
      setTimeout(() => {
        e.target.value = applyCpfMask(e.target.value)
      }, 0)
    })
  }
})

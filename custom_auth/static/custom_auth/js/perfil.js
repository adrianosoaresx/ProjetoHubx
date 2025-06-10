// Perfil JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

    // Initialize Navigation
    initNavigation()

    // Initialize Forms
    initForms()

    // Initialize Tabs
    initTabs()

    // Initialize Modals
    initModals()

    // Initialize Avatar Upload
    initAvatarUpload()

    // Initialize Password Strength
    initPasswordStrength()

    // Initialize Connection Actions
    initConnectionActions()

    // Initialize Account Settings
    initAccountSettings()
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

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item")
    const sections = document.querySelectorAll(".perfil-section")

    navItems.forEach((item) => {
        item.addEventListener("click", (e) => {
            e.preventDefault()

            // Remove active class from all nav items and sections
            navItems.forEach((nav) => nav.classList.remove("active"))
            sections.forEach((section) => section.classList.remove("active"))

            // Add active class to clicked nav item
            item.classList.add("active")

            // Show corresponding section
            const sectionId = item.dataset.section
            const targetSection = document.getElementById(sectionId)
            if (targetSection) {
                targetSection.classList.add("active")
            }
        })
    })
}

// Forms
function initForms() {
    const forms = document.querySelectorAll(".perfil-form")

    forms.forEach((form) => {
        form.addEventListener("submit", handleFormSubmission)
    })

    // Initialize form validation
    initFormValidation()
}

function handleFormSubmission(event) {
    event.preventDefault()

    const form = event.target
    const submitButton = form.querySelector('button[type="submit"]')
    const buttonText = submitButton.querySelector(".button-text")
    const buttonLoader = submitButton.querySelector(".button-loader")

    // Show loading state
    submitButton.classList.add("loading")
    submitButton.disabled = true

    // Simulate form submission
    setTimeout(() => {
        // Hide loading state
        submitButton.classList.remove("loading")
        submitButton.disabled = false

        // Show success message
        showNotification("Informações atualizadas com sucesso!", "success")

        // Here you would normally submit the form data to the server
        console.log("Form data:", new FormData(form))
    }, 2000)
}

function initFormValidation() {
    // Email validation
    const emailInput = document.getElementById("email")
    if (emailInput) {
        emailInput.addEventListener("blur", validateEmail)
    }

    // Username validation
    const usernameInput = document.getElementById("username")
    if (usernameInput) {
        usernameInput.addEventListener("blur", validateUsername)
    }

    // Phone validation
    const phoneInputs = document.querySelectorAll('input[type="tel"]')
    phoneInputs.forEach((input) => {
        input.addEventListener("input", formatPhone)
    })

    // CEP validation
    const cepInput = document.getElementById("cep")
    if (cepInput) {
        cepInput.addEventListener("input", formatCEP)
        cepInput.addEventListener("blur", validateCEP)
    }
}

function validateEmail(event) {
    const email = event.target.value.trim()
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

    if (email && !emailRegex.test(email)) {
        showFieldError(event.target, "Digite um email válido")
    } else {
        clearFieldError(event.target)
    }
}

function validateUsername(event) {
    const username = event.target.value.trim()

    if (username.length < 3) {
        showFieldError(event.target, "Nome de usuário deve ter pelo menos 3 caracteres")
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        showFieldError(event.target, "Use apenas letras, números e underscore (_)")
    } else {
        clearFieldError(event.target)
    }
}

function formatPhone(event) {
    let value = event.target.value.replace(/\D/g, "")

    if (value.length <= 11) {
        value = value.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3")
        value = value.replace(/(\d{2})(\d{4})(\d{4})/, "($1) $2-$3")
        value = value.replace(/(\d{2})(\d{4})/, "($1) $2")
        value = value.replace(/(\d{2})/, "($1")
    }

    event.target.value = value
}

function formatCEP(event) {
    let value = event.target.value.replace(/\D/g, "")
    value = value.replace(/(\d{5})(\d{3})/, "$1-$2")
    event.target.value = value
}

function validateCEP(event) {
    const cep = event.target.value.replace(/\D/g, "")

    if (cep.length === 8) {
        // Simulate CEP validation
        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then((response) => response.json())
            .then((data) => {
                if (!data.erro) {
                    // Fill address fields
                    const cidadeInput = document.getElementById("cidade")
                    const estadoInput = document.getElementById("estado")

                    if (cidadeInput) cidadeInput.value = data.localidade
                    if (estadoInput) estadoInput.value = data.uf

                    clearFieldError(event.target)
                } else {
                    showFieldError(event.target, "CEP não encontrado")
                }
            })
            .catch(() => {
                showFieldError(event.target, "Erro ao validar CEP")
            })
    }
}

function showFieldError(field, message) {
    field.classList.add("invalid")

    // Remove existing error message
    const existingError = field.parentNode.querySelector(".field-error")
    if (existingError) {
        existingError.remove()
    }

    // Add new error message
    const errorElement = document.createElement("div")
    errorElement.className = "field-error"
    errorElement.textContent = message
    errorElement.style.color = "var(--error-color)"
    errorElement.style.fontSize = "0.8rem"
    errorElement.style.marginTop = "0.3rem"

    field.parentNode.appendChild(errorElement)
}

function clearFieldError(field) {
    field.classList.remove("invalid")

    const errorElement = field.parentNode.querySelector(".field-error")
    if (errorElement) {
        errorElement.remove()
    }
}

// Tabs
function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn")
    const tabPanes = document.querySelectorAll(".tab-pane")

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const tabId = button.dataset.tab

            // Remove active class from all tabs
            tabButtons.forEach((btn) => btn.classList.remove("active"))
            tabPanes.forEach((pane) => pane.classList.remove("active"))

            // Add active class to clicked tab
            button.classList.add("active")
            const targetPane = document.getElementById(tabId)
            if (targetPane) {
                targetPane.classList.add("active")
            }
        })
    })
}

// Modals
function initModals() {
    const modals = document.querySelectorAll(".modal")
    const modalCloses = document.querySelectorAll(".modal-close")

    // Close modal when clicking close button
    modalCloses.forEach((close) => {
        close.addEventListener("click", () => {
            const modal = close.closest(".modal")
            closeModal(modal)
        })
    })

    // Close modal when clicking outside
    modals.forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                closeModal(modal)
            }
        })
    })

    // Close modal with Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const activeModal = document.querySelector(".modal.active")
            if (activeModal) {
                closeModal(activeModal)
            }
        }
    })
}

function openModal(modalId) {
    const modal = document.getElementById(modalId)
    if (modal) {
        modal.classList.add("active")
        document.body.style.overflow = "hidden"
    }
}

function closeModal(modal) {
    modal.classList.remove("active")
    document.body.style.overflow = ""
}

// Avatar Upload
function initAvatarUpload() {
    const avatarEditBtn = document.getElementById("avatarEditBtn")
    const avatarInput = document.getElementById("avatarInput")
    const avatarPreview = document.getElementById("avatarPreview")
    const saveAvatarBtn = document.getElementById("saveAvatar")
    const removeAvatarBtn = document.getElementById("removeAvatar")
    const cancelAvatarBtn = document.getElementById("cancelAvatar")

    if (avatarEditBtn) {
        avatarEditBtn.addEventListener("click", () => {
            openModal("avatarModal")
        })
    }

    if (avatarInput) {
        avatarInput.addEventListener("change", handleAvatarSelection)
    }

    if (saveAvatarBtn) {
        saveAvatarBtn.addEventListener("click", saveAvatar)
    }

    if (removeAvatarBtn) {
        removeAvatarBtn.addEventListener("click", removeAvatar)
    }

    if (cancelAvatarBtn) {
        cancelAvatarBtn.addEventListener("click", () => {
            closeModal(document.getElementById("avatarModal"))
        })
    }
}

function handleAvatarSelection(event) {
    const file = event.target.files[0]
    const avatarPreview = document.getElementById("avatarPreview")

    if (file) {
        // Validate file type
        const allowedTypes = ["image/jpeg", "image/jpg", "image/png"]
        if (!allowedTypes.includes(file.type)) {
            showNotification("Formato não suportado. Use JPG ou PNG", "error")
            event.target.value = ""
            return
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024
        if (file.size > maxSize) {
            showNotification("Arquivo muito grande. Máximo 5MB", "error")
            event.target.value = ""
            return
        }

        // Create preview
        const reader = new FileReader()
        reader.onload = (e) => {
            avatarPreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`
        }
        reader.readAsDataURL(file)
    }
}

function saveAvatar() {
    const avatarInput = document.getElementById("avatarInput")
    const file = avatarInput.files[0]

    if (file) {
        // Simulate avatar upload
        const formData = new FormData()
        formData.append("avatar", file)

        // Show loading state
        const saveBtn = document.getElementById("saveAvatar")
        saveBtn.textContent = "Salvando..."
        saveBtn.disabled = true

        setTimeout(() => {
            // Update main avatar
            const reader = new FileReader()
            reader.onload = (e) => {
                const mainAvatar = document.querySelector(".user-avatar")
                if (mainAvatar) {
                    mainAvatar.src = e.target.result
                } else {
                    // Replace placeholder with image
                    const avatarWrapper = document.querySelector(".avatar-wrapper")
                    avatarWrapper.innerHTML = `
            <img src="${e.target.result}" alt="Avatar" class="user-avatar">
            <button class="avatar-edit-btn" id="avatarEditBtn" title="Alterar foto">
              <span>📷</span>
            </button>
          `
                        // Re-initialize avatar edit button
                    document.getElementById("avatarEditBtn").addEventListener("click", () => {
                        openModal("avatarModal")
                    })
                }
            }
            reader.readAsDataURL(file)

            // Reset button
            saveBtn.textContent = "Salvar"
            saveBtn.disabled = false

            // Close modal
            closeModal(document.getElementById("avatarModal"))

            // Show success message
            showNotification("Avatar atualizado com sucesso!", "success")
        }, 2000)
    }
}

function removeAvatar() {
    const avatarWrapper = document.querySelector(".avatar-wrapper")
    const username = document.querySelector(".user-username").textContent.replace("@", "")

    avatarWrapper.innerHTML = `
    <div class="avatar-placeholder">
      <span>${username.charAt(0).toUpperCase()}</span>
    </div>
    <button class="avatar-edit-btn" id="avatarEditBtn" title="Alterar foto">
      <span>📷</span>
    </button>
  `

    // Re-initialize avatar edit button
    document.getElementById("avatarEditBtn").addEventListener("click", () => {
        openModal("avatarModal")
    })

    // Reset modal preview
    const avatarPreview = document.getElementById("avatarPreview")
    avatarPreview.innerHTML = `
    <div class="avatar-placeholder">
      <span>${username.charAt(0).toUpperCase()}</span>
    </div>
  `

    // Clear file input
    document.getElementById("avatarInput").value = ""

    // Close modal
    closeModal(document.getElementById("avatarModal"))

    // Show success message
    showNotification("Avatar removido com sucesso!", "success")
}

// Password Strength
function initPasswordStrength() {
    const novaSenhaInput = document.getElementById("nova_senha")
    const strengthFill = document.getElementById("strengthFill")
    const strengthText = document.getElementById("strengthText")

    if (novaSenhaInput && strengthFill && strengthText) {
        novaSenhaInput.addEventListener("input", function() {
            const senha = this.value
            updatePasswordStrength(senha, strengthFill, strengthText)
        })
    }

    // Password confirmation validation
    const confirmarSenhaInput = document.getElementById("confirmar_senha")
    if (confirmarSenhaInput) {
        confirmarSenhaInput.addEventListener("input", validatePasswordMatch)
    }
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

function validatePasswordMatch() {
    const novaSenha = document.getElementById("nova_senha").value
    const confirmarSenha = document.getElementById("confirmar_senha").value
    const confirmarSenhaInput = document.getElementById("confirmar_senha")

    if (confirmarSenha.length > 0) {
        if (novaSenha !== confirmarSenha) {
            showFieldError(confirmarSenhaInput, "As senhas não coincidem")
        } else {
            clearFieldError(confirmarSenhaInput)
        }
    }
}

// Connection Actions
function initConnectionActions() {
    // Accept/Reject connection requests
    const acceptButtons = document.querySelectorAll(".btn-accept")
    const rejectButtons = document.querySelectorAll(".btn-reject")

    acceptButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const requestId = btn.dataset.id
            handleConnectionRequest(requestId, "accept", btn)
        })
    })

    rejectButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const requestId = btn.dataset.id
            handleConnectionRequest(requestId, "reject", btn)
        })
    })

    // Connect/Unfollow actions
    const connectButtons = document.querySelectorAll(".btn-connect")
    const unfollowButtons = document.querySelectorAll(".btn-unfollow")

    connectButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const userId = btn.dataset.id
            handleConnect(userId, btn)
        })
    })

    unfollowButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const userId = btn.dataset.id
            handleUnfollow(userId, btn)
        })
    })
}

function handleConnectionRequest(requestId, action, button) {
    button.disabled = true
    button.textContent = action === "accept" ? "Aceitando..." : "Recusando..."

    // Simulate API call
    setTimeout(() => {
        if (action === "accept") {
            showNotification("Solicitação de conexão aceita!", "success")
        } else {
            showNotification("Solicitação de conexão recusada!", "info")
        }

        // Remove the request card
        const requestCard = button.closest(".request-card")
        if (requestCard) {
            requestCard.style.animation = "fadeOut 0.3s ease"
            setTimeout(() => {
                requestCard.remove()
            }, 300)
        }
    }, 1000)
}

function handleConnect(userId, button) {
    button.disabled = true
    button.textContent = "Conectando..."

    // Simulate API call
    setTimeout(() => {
        button.textContent = "Conectado"
        button.classList.remove("btn-connect")
        button.classList.add("connection-badge")
        button.disabled = false

        showNotification("Solicitação de conexão enviada!", "success")
    }, 1000)
}

function handleUnfollow(userId, button) {
    button.disabled = true
    button.textContent = "Deixando de seguir..."

    // Simulate API call
    setTimeout(() => {
        showNotification("Você deixou de seguir este usuário", "info")

        // Remove the following card
        const followingCard = button.closest(".following-card")
        if (followingCard) {
            followingCard.style.animation = "fadeOut 0.3s ease"
            setTimeout(() => {
                followingCard.remove()
            }, 300)
        }
    }, 1000)
}

// Account Settings
function initAccountSettings() {
    const btn2FA = document.getElementById("btn2FA")
    const btnDesativarConta = document.getElementById("btnDesativarConta")
    const btnExcluirConta = document.getElementById("btnExcluirConta")
    const btnSalvarConfiguracoes = document.getElementById("btnSalvarConfiguracoes")

    if (btn2FA) {
        btn2FA.addEventListener("click", () => {
            showNotification("Funcionalidade de 2FA será implementada em breve!", "info")
        })
    }

    if (btnDesativarConta) {
        btnDesativarConta.addEventListener("click", () => {
            showConfirmModal(
                "Desativar Conta",
                "Tem certeza que deseja desativar sua conta? Você poderá reativá-la a qualquer momento.",
                () => {
                    showNotification("Conta desativada com sucesso!", "info")
                },
            )
        })
    }

    if (btnExcluirConta) {
        btnExcluirConta.addEventListener("click", () => {
            showConfirmModal(
                "Excluir Conta",
                "ATENÇÃO: Esta ação é irreversível! Todos os seus dados serão permanentemente excluídos. Tem certeza que deseja continuar?",
                () => {
                    showNotification("Conta excluída com sucesso!", "error")
                        // Redirect to home page after a delay
                    setTimeout(() => {
                        window.location.href = "/"
                    }, 2000)
                },
            )
        })
    }

    if (btnSalvarConfiguracoes) {
        btnSalvarConfiguracoes.addEventListener("click", () => {
            const button = btnSalvarConfiguracoes
            button.classList.add("loading")
            button.disabled = true

            setTimeout(() => {
                button.classList.remove("loading")
                button.disabled = false
                showNotification("Configurações salvas com sucesso!", "success")
            }, 2000)
        })
    }
}

function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById("confirmModal")
    const titleElement = document.getElementById("confirmTitle")
    const messageElement = document.getElementById("confirmMessage")
    const confirmButton = document.getElementById("confirmAction")
    const cancelButton = document.getElementById("cancelAction")

    titleElement.textContent = title
    messageElement.textContent = message

    // Remove existing event listeners
    const newConfirmButton = confirmButton.cloneNode(true)
    confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton)

    const newCancelButton = cancelButton.cloneNode(true)
    cancelButton.parentNode.replaceChild(newCancelButton, cancelButton)

    // Add new event listeners
    newConfirmButton.addEventListener("click", () => {
        closeModal(modal)
        onConfirm()
    })

    newCancelButton.addEventListener("click", () => {
        closeModal(modal)
    })

    openModal("confirmModal")
}

// Notifications
function showNotification(message, type = "info") {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll(".notification")
    existingNotifications.forEach((notification) => notification.remove())

    // Create notification element
    const notification = document.createElement("div")
    notification.className = `notification notification-${type}`
    notification.innerHTML = `
    <div class="notification-content">
      <span class="notification-icon">${getNotificationIcon(type)}</span>
      <span class="notification-message">${message}</span>
      <button class="notification-close">&times;</button>
    </div>
  `

    // Add styles
    notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    background: rgba(13, 27, 13, 0.95);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    padding: 1rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(20px);
    max-width: 400px;
    animation: slideIn 0.3s ease;
  `

    // Add type-specific styles
    if (type === "success") {
        notification.style.borderColor = "var(--success-color)"
    } else if (type === "error") {
        notification.style.borderColor = "var(--error-color)"
    } else if (type === "warning") {
        notification.style.borderColor = "var(--warning-color)"
    } else {
        notification.style.borderColor = "var(--matrix-green)"
    }

    // Add to document
    document.body.appendChild(notification)

    // Add close functionality
    const closeBtn = notification.querySelector(".notification-close")
    closeBtn.addEventListener("click", () => {
        notification.style.animation = "slideOut 0.3s ease"
        setTimeout(() => {
            notification.remove()
        }, 300)
    })

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = "slideOut 0.3s ease"
            setTimeout(() => {
                notification.remove()
            }, 300)
        }
    }, 5000)

    // Add CSS animations if not already added
    if (!document.querySelector("#notification-styles")) {
        const style = document.createElement("style")
        style.id = "notification-styles"
        style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      
      @keyframes slideOut {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(100%);
          opacity: 0;
        }
      }
      
      .notification-content {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        color: var(--white);
      }
      
      .notification-icon {
        font-size: 1.2rem;
      }
      
      .notification-message {
        flex: 1;
        font-size: 0.9rem;
      }
      
      .notification-close {
        background: none;
        border: none;
        color: rgba(255, 255, 255, 0.7);
        font-size: 1.2rem;
        cursor: pointer;
        padding: 0.2rem;
        border-radius: 50%;
        transition: all 0.3s ease;
      }
      
      .notification-close:hover {
        background: rgba(255, 255, 255, 0.1);
        color: var(--white);
      }
    `
        document.head.appendChild(style)
    }
}

function getNotificationIcon(type) {
    switch (type) {
        case "success":
            return "✅"
        case "error":
            return "❌"
        case "warning":
            return "⚠️"
        default:
            return "ℹ️"
    }
}

// Search functionality
function initSearch() {
    const searchInputs = document.querySelectorAll(".search-input")

    searchInputs.forEach((input) => {
        input.addEventListener("input", (e) => {
            const searchTerm = e.target.value.toLowerCase()
            const container = input.closest(".tab-pane")
            const cards = container.querySelectorAll(".connection-card, .follower-card, .following-card")

            cards.forEach((card) => {
                const name = card.querySelector("h4").textContent.toLowerCase()
                const username = card.querySelector("p").textContent.toLowerCase()

                if (name.includes(searchTerm) || username.includes(searchTerm)) {
                    card.style.display = "flex"
                } else {
                    card.style.display = "none"
                }
            })
        })
    })
}

// Initialize search when DOM is loaded
document.addEventListener("DOMContentLoaded", initSearch)

// Utility function to get CSRF token
function getCsrfToken() {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
    return csrfToken ? csrfToken.value : ""
}

// Add fade out animation CSS
const fadeOutStyle = document.createElement("style")
fadeOutStyle.textContent = `
  @keyframes fadeOut {
    from {
      opacity: 1;
      transform: scale(1);
    }
    to {
      opacity: 0;
      transform: scale(0.95);
    }
  }
`
document.head.appendChild(fadeOutStyle)
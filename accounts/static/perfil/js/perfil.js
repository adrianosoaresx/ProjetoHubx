// Perfil JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

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

    // Initialize Company Form toggle
    initEmpresaFormToggle()
})

// REMOVIDO: initNavigation() para navegação controlada pelo Django

// Matrix Code Rain Effect
function initMatrixRain() {
    const matrixContainer = document.getElementById("matrixCode")
    if (!matrixContainer) return

    const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$+-*/=%\"'#&_(),.;:?!\\|{}<>[]^~"
    const columnCount = 15

    for (let i = 0; i < columnCount; i++) {
        const column = document.createElement("div")
        column.className = "code-column"

        column.style.left = `${Math.random() * 100}%`
        column.style.animationDuration = `${Math.random() * 15 + 8}s`
        column.style.animationDelay = `${Math.random() * 5}s`

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

// (demais funções seguem iguais até o fim do arquivo)

function initTabs() {
    const tabs = document.querySelectorAll('[role="tab"]')
    tabs.forEach(tab => {
        tab.addEventListener('click', ev => {
            if (tab.tagName === 'A') ev.preventDefault()
            tabs.forEach(t => {
                const selected = t === tab
                t.setAttribute('aria-selected', String(selected))
                const targetId = t.getAttribute('aria-controls') || t.dataset.tabTarget || (t.getAttribute('href') || '').replace(/^#/, '')
                if (!targetId) return
                const section = document.getElementById(targetId)
                if (section) section.hidden = !selected
            })
        })
    })
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

document.addEventListener("DOMContentLoaded", initSearch)


function getCsrfToken() {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
    return csrfToken ? csrfToken.value : ""
}

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

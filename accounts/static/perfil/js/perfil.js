// Perfil JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

    // Initialize Tabs
    initTabs()

    // Initialize Perfil navigation
    initPerfilNavigation()

    // Initialize optional helpers when available
    const optionalInitializers = [
        "initForms",
        "initModals",
        "initAvatarUpload",
        "initPasswordStrength",
        "initConnectionActions",
        "initAccountSettings",
        "initEmpresaFormToggle",
    ]

    optionalInitializers.forEach(name => {
        const initializer = globalThis[name]
        if (typeof initializer === "function") {
            try {
                initializer()
            } catch (error) {
                console.error(`Erro ao executar ${name}:`, error)
            }
        }
    })
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

export function initTabs() {
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
                if (section) {
                    section.hidden = !selected
                    section.setAttribute('aria-hidden', selected ? 'false' : 'true')
                }
            })
        })
    })
}

function initPerfilNavigation() {
    const container = document.getElementById('perfil-content')
    if (!container) return

    const navLinks = Array.from(document.querySelectorAll('[data-perfil-nav]'))
    const defaultUrl = container.dataset.perfilDefaultUrl || null
    const defaultSection = container.dataset.perfilDefaultSection || null
    const loadingText = container.dataset.perfilLoadingText || 'Carregando conteúdo...'
    const errorText = container.dataset.perfilErrorText || 'Não foi possível carregar esta seção.'
    const mode = container.dataset.perfilMode || 'owner'
    const publicId = container.dataset.perfilPublicId || ''
    const username = container.dataset.perfilUsername || ''
    let activeLink = null
    let activeSection = defaultSection
    let activeUrl = null
    let controller = null

    const prepareUrl = rawUrl => {
        if (!rawUrl) return null
        const url = new URL(rawUrl, window.location.origin)
        if (mode !== 'owner') {
            if (publicId && !url.searchParams.has('public_id')) {
                url.searchParams.set('public_id', publicId)
            } else if (username && !url.searchParams.has('username')) {
                url.searchParams.set('username', username)
            }
        }
        return url.toString()
    }

    const showLoading = () => {
        container.innerHTML = `<div class="py-6 text-center text-sm text-[var(--text-secondary)]">${loadingText}</div>`
        container.setAttribute('aria-busy', 'true')
    }

    const showError = () => {
        container.innerHTML = `<div class="py-6 text-center text-sm text-red-600">${errorText}</div>`
    }

    const setActive = link => {
        activeLink = link || null
        navLinks.forEach(item => {
            const isActive = item === link
            item.classList.toggle('is-active', isActive)
            if (isActive) {
                item.setAttribute('aria-current', 'page')
            } else {
                item.removeAttribute('aria-current')
            }
        })
    }

    const loadSection = async (url, section) => {
        if (!url) return

        if (controller) {
            controller.abort()
        }
        controller = new AbortController()
        activeUrl = url
        if (section) {
            activeSection = section
            container.dataset.perfilActiveSection = section
        }

        showLoading()

        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
                signal: controller.signal,
            })

            if (!response.ok) {
                throw new Error(`Failed to load section: ${section || 'unknown'}`)
            }

            const html = await response.text()
            container.innerHTML = html
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error(error)
                showError()
            }
        } finally {
            container.setAttribute('aria-busy', 'false')
            controller = null
        }
    }

    const handleLink = (link, options = {}) => {
        const section = options.section || link?.dataset.perfilSection || defaultSection
        const rawUrl = options.url || link?.dataset.perfilUrl || defaultUrl
        const finalUrl = prepareUrl(rawUrl)
        if (!finalUrl) return

        setActive(link || activeLink)
        loadSection(finalUrl, section)
    }

    navLinks.forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault()
            handleLink(link)
        })
    })

    container.addEventListener('submit', event => {
        const form = event.target
        if (!(form instanceof HTMLFormElement)) return

        const method = (form.method || 'get').toLowerCase()
        if (method !== 'get' || form.hasAttribute('data-perfil-native')) {
            return
        }

        event.preventDefault()
        const action = form.getAttribute('action') || activeUrl || defaultUrl
        if (!action) return

        const url = new URL(action, window.location.origin)
        const formData = new FormData(form)
        for (const [key, value] of formData.entries()) {
            if (typeof value === 'string') {
                if (value) {
                    url.searchParams.set(key, value)
                } else {
                    url.searchParams.delete(key)
                }
            }
        }

        handleLink(activeLink, { url: url.toString(), section: activeSection })
    })

    const defaultLink = navLinks.find(link => link.dataset.perfilDefault === 'true') || navLinks[0] || null
    if (defaultLink) {
        handleLink(defaultLink, {
            section: defaultLink.dataset.perfilSection || defaultSection,
            url: defaultUrl || defaultLink.dataset.perfilUrl,
        })
    } else if (defaultUrl) {
        const finalUrl = prepareUrl(defaultUrl)
        loadSection(finalUrl, defaultSection)
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

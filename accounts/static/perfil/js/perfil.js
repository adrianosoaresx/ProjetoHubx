// Perfil JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

    // Initialize Tabs
    initTabs()

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

    initConnectionReturn()
    // Marca a aba ativa quando usando HTMX
    initPerfilActiveHighlight()
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

// Fade-out style for optional UI effects
const fadeOutStyle = document.createElement("style")
fadeOutStyle.textContent = `
  @keyframes fadeOut {
    from { opacity: 1; transform: scale(1); }
    to { opacity: 0; transform: scale(0.95); }
  }
`
document.head.appendChild(fadeOutStyle)

// Marca a aba ativa (HTMX e carga inicial)
function initPerfilActiveHighlight() {
    const activeClasses = [
        'is-active',
        'border-transparent',
        'bg-[var(--primary)]',
        'text-[var(--text-inverse)]',
        'shadow-sm',
    ]
    const inactiveClasses = ['text-[var(--text-secondary)]']

    const setActiveBySection = (section) => {
        const navLinks = Array.from(document.querySelectorAll('[data-perfil-nav]'))
        if (navLinks.length === 0) return

        let target = null
        if (section) {
            target = navLinks.find(a => (a.dataset.perfilSection || '') === section) || null
        }
        if (!target) {
            target = navLinks.find(a => a.dataset.perfilDefault === 'true') || navLinks[0] || null
        }

        navLinks.forEach(item => {
            const isActive = item === target
            activeClasses.forEach(c => item.classList.toggle(c, isActive))
            inactiveClasses.forEach(c => item.classList.toggle(c, !isActive))
            if (isActive) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current')
        })
    }

    const getUrlSection = () => {
        try { return new URLSearchParams(location.search).get('section') } catch { return null }
    }

    // Carga inicial
    setActiveBySection(getUrlSection())

    // Antes da requisição HTMX (clique em aba)
    document.addEventListener('htmx:beforeRequest', (ev) => {
        const el = ev.detail && ev.detail.elt
        if (!(el instanceof Element)) return
        const link = el.closest('[data-perfil-nav]')
        if (link) {
            const section = link.dataset.perfilSection || null
            setActiveBySection(section)
        }
    })

    // Após carregar o conteúdo no destino
    document.addEventListener('htmx:afterOnLoad', (ev) => {
        const target = ev.detail && ev.detail.target
        if (target && target.id === 'perfil-content') {
            setActiveBySection(getUrlSection())
        }
    })

    // Suporte a back/forward do navegador
    window.addEventListener('popstate', () => {
        setActiveBySection(getUrlSection())
    })
}

function initConnectionReturn() {
    const STORAGE_KEY = "perfilConnectionReturn"

    const getLocationKey = () => `${location.pathname}${location.search}`

    const saveAnchor = anchorId => {
        if (!anchorId) return
        try {
            const payload = {
                anchor: anchorId,
                url: getLocationKey(),
                timestamp: Date.now(),
            }
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
        } catch (error) {
            console.warn("Não foi possível salvar a posição da conexão:", error)
        }
    }

    const attachHandlers = (root = document) => {
        const links = root.querySelectorAll("[data-connection-link]")
        links.forEach(link => {
            if (link.dataset.connectionLinkBound === "true") return
            link.addEventListener("click", () => {
                saveAnchor(link.dataset.connectionLink || "")
            })
            link.dataset.connectionLinkBound = "true"
        })
    }

    const restorePosition = root => {
        let stored
        try {
            stored = sessionStorage.getItem(STORAGE_KEY)
        } catch (error) {
            return
        }
        if (!stored) return

        let data
        try {
            data = JSON.parse(stored)
        } catch (error) {
            sessionStorage.removeItem(STORAGE_KEY)
            return
        }

        if (!data || data.url !== getLocationKey() || !data.anchor) {
            return
        }

        const targetElement = document.getElementById(data.anchor)
        if (!(targetElement instanceof Element)) {
            return
        }

        if (root instanceof Element && !root.contains(targetElement)) {
            return
        }

        requestAnimationFrame(() => {
            targetElement.scrollIntoView({ behavior: "smooth", block: "center" })
        })

        try {
            sessionStorage.removeItem(STORAGE_KEY)
        } catch (error) {
            console.warn("Não foi possível limpar o estado da conexão:", error)
        }
    }

    attachHandlers()
    restorePosition(document)

    document.addEventListener("htmx:afterOnLoad", event => {
        const target = event.detail && event.detail.target
        if (!(target instanceof Element) || target.id !== "perfil-content") return
        attachHandlers(target)
        restorePosition(target)
    })

    window.addEventListener("pageshow", event => {
        if (event.persisted) {
            restorePosition(document)
        }
    })
}

// Register Page JavaScript - HubX

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Matrix Code Rain Effect
    initMatrixRain()

    // Initialize Form Validation
    initFormValidation()

    // Initialize Password Strength Checker
    initPasswordStrength()

    // Initialize Form Submission
    initFormSubmission()
})

// Matrix Code Rain Effect
function initMatrixRain() {
    const matrixContainer = document.getElementById("matrixCode")
    const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$+-*/=%\"'#&_(),.;:?!\\|{}<>[]^~"
    const columnCount = 20

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
    const form = document.getElementById("registerForm")
    const inputs = form.querySelectorAll(".form-input")

    inputs.forEach((input) => {
        input.addEventListener("blur", validateField)
        input.addEventListener("input", clearValidation)
    })

    // Real-time username validation
    const usernameInput = document.getElementById("username")
    let usernameTimeout

    usernameInput.addEventListener("input", function() {
        clearTimeout(usernameTimeout)
        usernameTimeout = setTimeout(() => {
            validateUsername(this.value)
        }, 500)
    })

    // Real-time email validation
    const emailInput = document.getElementById("email")
    emailInput.addEventListener("input", function() {
        validateEmail(this.value)
    })

    // Password confirmation validation
    const password1 = document.getElementById("password1")
    const password2 = document.getElementById("password2")

    password2.addEventListener("input", function() {
        validatePasswordMatch(password1.value, this.value)
    })
}

function validateField(event) {
    const field = event.target
    const value = field.value.trim()
    const fieldName = field.name

    switch (fieldName) {
        case "first_name":
        case "last_name":
            validateName(field, value)
            break
        case "username":
            validateUsername(value)
            break
        case "email":
            validateEmail(value)
            break
        case "token":
            validateToken(value)
            break
        case "password1":
            validatePassword(value)
            break
        case "password2":
            validatePasswordMatch(document.getElementById("password1").value, value)
            break
    }
}

function validateName(field, value) {
    const validation = document.getElementById(`${field.name}_validation`)

    if (value.length < 2) {
        showValidation(field, validation, "Nome deve ter pelo menos 2 caracteres", false)
    } else if (!/^[a-zA-ZÀ-ÿ\s]+$/.test(value)) {
        showValidation(field, validation, "Nome deve conter apenas letras", false)
    } else {
        showValidation(field, validation, "Nome válido", true)
    }
}

function validateUsername(value) {
    const field = document.getElementById("username")
    const validation = document.getElementById("username_validation")

    if (value.length < 3) {
        showValidation(field, validation, "Nome de usuário deve ter pelo menos 3 caracteres", false)
    } else if (!/^[a-zA-Z0-9_]+$/.test(value)) {
        showValidation(field, validation, "Use apenas letras, números e underscore", false)
    } else {
        // Simulate API call to check username availability
        showValidation(field, validation, "Verificando disponibilidade...", null)

        setTimeout(() => {
            // Simulate random availability check
            const isAvailable = Math.random() > 0.3
            if (isAvailable) {
                showValidation(field, validation, "Nome de usuário disponível", true)
            } else {
                showValidation(field, validation, "Nome de usuário já está em uso", false)
            }
        }, 1000)
    }
}

function validateEmail(value) {
    const field = document.getElementById("email")
    const validation = document.getElementById("email_validation")
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

    if (!emailRegex.test(value)) {
        showValidation(field, validation, "Digite um e-mail válido", false)
    } else {
        showValidation(field, validation, "E-mail válido", true)
    }
}

function validateToken(value) {
    const field = document.getElementById("token")
    const validation = document.getElementById("token_validation")

    if (value.length < 10) {
        showValidation(field, validation, "Token deve ter pelo menos 10 caracteres", false)
    } else {
        showValidation(field, validation, "Token válido", true)
    }
}

function validatePassword(value) {
    const field = document.getElementById("password1")
    const validation = document.getElementById("password1_validation")

    const hasLength = value.length >= 8
    const hasUpper = /[A-Z]/.test(value)
    const hasLower = /[a-z]/.test(value)
    const hasNumber = /\d/.test(value)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(value)

    const score = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length

    if (score < 3) {
        showValidation(field, validation, "Senha muito fraca", false)
    } else if (score < 4) {
        showValidation(field, validation, "Senha moderada", null)
    } else {
        showValidation(field, validation, "Senha forte", true)
    }
}

function validatePasswordMatch(password1, password2) {
    const field = document.getElementById("password2")
    const validation = document.getElementById("password2_validation")

    if (password2.length === 0) {
        showValidation(field, validation, "", null)
    } else if (password1 !== password2) {
        showValidation(field, validation, "Senhas não coincidem", false)
    } else {
        showValidation(field, validation, "Senhas coincidem", true)
    }
}

function showValidation(field, validationElement, message, isValid) {
    validationElement.textContent = message

    // Remove previous classes
    field.classList.remove("valid", "invalid")
    validationElement.classList.remove("valid", "invalid")

    if (isValid === true) {
        field.classList.add("valid")
        validationElement.classList.add("valid")
    } else if (isValid === false) {
        field.classList.add("invalid")
        validationElement.classList.add("invalid")
    }
}

function clearValidation(event) {
    const field = event.target
    const validation = document.getElementById(`${field.name}_validation`)

    if (validation && field.value.trim() === "") {
        field.classList.remove("valid", "invalid")
        validation.classList.remove("valid", "invalid")
        validation.textContent = ""
    }
}

// Password Strength Checker
function initPasswordStrength() {
    const passwordInput = document.getElementById("password1")
    const strengthFill = document.getElementById("strengthFill")
    const strengthText = document.getElementById("strengthText")

    passwordInput.addEventListener("input", function() {
        const password = this.value
        const strength = calculatePasswordStrength(password)

        updateStrengthIndicator(strengthFill, strengthText, strength)
    })
}

function calculatePasswordStrength(password) {
    if (password.length === 0) {
        return { score: 0, text: "Digite uma senha" }
    }

    const hasLength = password.length >= 8
    const hasUpper = /[A-Z]/.test(password)
    const hasLower = /[a-z]/.test(password)
    const hasNumber = /\d/.test(password)
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password)

    const score = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length

    const strengthLevels = [
        { score: 0, text: "Muito fraca", width: 0 },
        { score: 1, text: "Fraca", width: 20 },
        { score: 2, text: "Regular", width: 40 },
        { score: 3, text: "Boa", width: 60 },
        { score: 4, text: "Forte", width: 80 },
        { score: 5, text: "Muito forte", width: 100 },
    ]

    return strengthLevels[score] || strengthLevels[0]
}

function updateStrengthIndicator(fillElement, textElement, strength) {
    fillElement.style.width = `${strength.width}%`
    textElement.textContent = strength.text

    // Update color based on strength
    if (strength.score <= 2) {
        fillElement.style.background = "#ff4757"
    } else if (strength.score <= 3) {
        fillElement.style.background = "#ffa502"
    } else {
        fillElement.style.background = "var(--matrix-green)"
    }
}

// Form Submission
function initFormSubmission() {
    const form = document.getElementById("registerForm")
    const submitButton = document.getElementById("submitButton")
    const buttonText = submitButton.querySelector(".button-text")
    const buttonLoader = document.getElementById("buttonLoader")

    form.addEventListener("submit", (event) => {
        event.preventDefault()

        // Show loading state
        submitButton.classList.add("loading")
        submitButton.disabled = true

        // Simulate form submission
        setTimeout(() => {
            // Hide loading state
            submitButton.classList.remove("loading")
            submitButton.disabled = false

            // Here you would normally submit the form
            // form.submit();

            alert("Cadastro realizado com sucesso! (Simulação)")
        }, 2000)
    })
}


// Animação específica para onboarding
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar efeito de entrada suave
    const card = document.querySelector('.onboarding-card');
    card.style.opacity = '0';
    card.style.transform = 'translateY(30px)';

    setTimeout(() => {
        card.style.transition = 'all 0.8s ease';
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
    }, 100);

    // Animação sequencial dos features
    const features = document.querySelectorAll('.feature-item');
    features.forEach((feature, index) => {
        feature.style.opacity = '0';
        feature.style.transform = 'translateY(20px)';

        setTimeout(() => {
            feature.style.transition = 'all 0.6s ease';
            feature.style.opacity = '1';
            feature.style.transform = 'translateY(0)';
        }, 300 + (index * 100));
    });

    // Efeito de digitação no título
    const title = document.querySelector('.onboarding-title');
    const originalText = title.textContent;
    title.textContent = '';

    let i = 0;
    const typeWriter = () => {
        if (i < originalText.length) {
            title.textContent += originalText.charAt(i);
            i++;
            setTimeout(typeWriter, 100);
        }
    };

    setTimeout(typeWriter, 1000);
});
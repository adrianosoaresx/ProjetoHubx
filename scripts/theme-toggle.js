/**
 * Theme Toggle Functionality
 * Handles switching between light and dark themes
 */

class ThemeManager {
  constructor() {
    this.themeToggle = document.getElementById("themeToggle")
    this.currentTheme = this.getStoredTheme() || this.getPreferredTheme()

    this.init()
  }

  init() {
    // Set initial theme
    this.setTheme(this.currentTheme)

    // Add event listener to toggle button
    if (this.themeToggle) {
      this.themeToggle.addEventListener("click", () => {
        this.toggleTheme()
      })
    }

    // Listen for system theme changes
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!this.getStoredTheme()) {
        this.setTheme(e.matches ? "dark" : "light")
      }
    })

    // Update toggle button state
    this.updateToggleButton()
  }

  getStoredTheme() {
    return localStorage.getItem("theme")
  }

  getPreferredTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  }

  setTheme(theme) {
    this.currentTheme = theme

    // Remove existing theme classes
    document.documentElement.classList.remove("theme-light", "theme-dark")

    // Add new theme class
    document.documentElement.classList.add(`theme-${theme}`)

    // Store theme preference
    localStorage.setItem("theme", theme)

    // Update toggle button
    this.updateToggleButton()

    // Dispatch custom event
    window.dispatchEvent(
      new CustomEvent("themeChanged", {
        detail: { theme },
      }),
    )
  }

  toggleTheme() {
    const newTheme = this.currentTheme === "light" ? "dark" : "light"
    this.setTheme(newTheme)
  }

  updateToggleButton() {
    if (!this.themeToggle) return

    const isDark = this.currentTheme === "dark"
    const lightIcon = this.themeToggle.querySelector(".theme-icon-light")
    const darkIcon = this.themeToggle.querySelector(".theme-icon-dark")

    // Toggle button state
    this.themeToggle.classList.toggle("dark", isDark)

    // Toggle icons
    if (lightIcon && darkIcon) {
      lightIcon.style.display = isDark ? "none" : "block"
      darkIcon.style.display = isDark ? "block" : "none"
    }

    // Update aria-label for accessibility
    this.themeToggle.setAttribute("aria-label", isDark ? "Mudar para tema claro" : "Mudar para tema escuro")
  }

  getCurrentTheme() {
    return this.currentTheme
  }
}

// Initialize theme manager when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  window.themeManager = new ThemeManager()
})

// Utility functions for external use
window.setTheme = (theme) => {
  if (window.themeManager) {
    window.themeManager.setTheme(theme)
  }
}

window.toggleTheme = () => {
  if (window.themeManager) {
    window.themeManager.toggleTheme()
  }
}

window.getCurrentTheme = () => {
  return window.themeManager ? window.themeManager.getCurrentTheme() : "light"
}

// Example of listening to theme changes
window.addEventListener("themeChanged", (event) => {
  console.log("Theme changed to:", event.detail.theme)

  // You can add custom logic here when theme changes

  // Example: Update chart colors, refresh components, etc.
  // updateChartTheme(event.detail.theme);
  // refreshDataVisualization();
})

// Keyboard shortcut for theme toggle (Ctrl/Cmd + Shift + T)
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === "T") {
    event.preventDefault()
    window.toggleTheme()
  }
})

// Auto-detect system theme changes and update accordingly
const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
mediaQuery.addEventListener("change", (event) => {
  // Only auto-switch if user hasn't manually set a preference
  if (!localStorage.getItem("theme")) {
    window.setTheme(event.matches ? "dark" : "light")
  }
})

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
  module.exports = ThemeManager
}

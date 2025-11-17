(function () {
  const dropdown = document.getElementById("notification-dropdown");
  const bellButton = document.getElementById("notification-bell");

  if (!dropdown || !bellButton) return;

  const indicator = bellButton.querySelector("[data-dropdown-indicator]");
  const dropdownUrl = bellButton.dataset.dropdownUrl || bellButton.getAttribute("hx-get");
  const state = { open: false, hasLoaded: false };

  const setExpanded = (expanded) => {
    bellButton.setAttribute("aria-expanded", String(expanded));
    if (indicator) {
      indicator.classList.toggle("rotate-180", expanded);
    }
  };

  const focusMenuItem = (index) => {
    const items = Array.from(dropdown.querySelectorAll('[role="menuitem"]'));
    if (!items.length) return;
    const boundedIndex = (index + items.length) % items.length;
    items[boundedIndex].focus();
  };

  const ensureContentLoaded = () => {
    if (state.hasLoaded || !dropdownUrl) return;
    if (window.htmx && typeof window.htmx.ajax === "function") {
      window.htmx.ajax("GET", dropdownUrl, { target: "#notification-dropdown", swap: "innerHTML" });
      return;
    }

    fetch(dropdownUrl, { headers: { "HX-Request": "true" } })
      .then((response) => response.text())
      .then((html) => {
        dropdown.innerHTML = html;
        state.hasLoaded = true;
      })
      .catch(() => undefined);
  };

  const openDropdown = () => {
    ensureContentLoaded();
    dropdown.classList.remove("hidden");
    state.open = true;
    setExpanded(true);
  };

  const closeDropdown = () => {
    dropdown.classList.add("hidden");
    state.open = false;
    setExpanded(false);
  };

  const toggleDropdown = () => {
    if (state.open) {
      closeDropdown();
      return;
    }

    openDropdown();
    focusMenuItem(0);
  };

  const handleDocumentClick = (event) => {
    if (!state.open) return;
    if (dropdown.contains(event.target) || bellButton.contains(event.target)) return;
    closeDropdown();
  };

  const handleMenuKeydown = (event) => {
    if (!state.open) return;

    const items = Array.from(dropdown.querySelectorAll('[role="menuitem"]'));
    const currentIndex = items.indexOf(document.activeElement);

    switch (event.key) {
      case "Escape":
        closeDropdown();
        bellButton.focus();
        event.preventDefault();
        break;
      case "ArrowDown":
        focusMenuItem((currentIndex + 1) || 0);
        event.preventDefault();
        break;
      case "ArrowUp":
        focusMenuItem(currentIndex === -1 ? items.length - 1 : currentIndex - 1);
        event.preventDefault();
        break;
      case "Home":
        focusMenuItem(0);
        event.preventDefault();
        break;
      case "End":
        focusMenuItem(items.length - 1);
        event.preventDefault();
        break;
      case "Enter":
      case " ":
        if (document.activeElement && typeof document.activeElement.click === "function") {
          document.activeElement.click();
          event.preventDefault();
        }
        break;
      default:
        break;
    }
  };

  bellButton.addEventListener("click", toggleDropdown);

  bellButton.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!state.open) {
        openDropdown();
      }
      focusMenuItem(event.key === "ArrowDown" ? 0 : -1);
    }
    if (event.key === "Escape" && state.open) {
      closeDropdown();
    }
  });

  dropdown.addEventListener("keydown", handleMenuKeydown);
  document.addEventListener("click", handleDocumentClick);

  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target === dropdown) {
      state.hasLoaded = true;
      if (state.open) {
        focusMenuItem(0);
      }
    }
  });

  window.HubxNotificationDropdown = {
    refresh: () => {
      if (!dropdownUrl) return;
      if (window.htmx && typeof window.htmx.ajax === "function") {
        window.htmx.ajax("GET", dropdownUrl, { target: "#notification-dropdown", swap: "innerHTML" });
        return;
      }

      fetch(dropdownUrl, { headers: { "HX-Request": "true" } })
        .then((response) => response.text())
        .then((html) => {
          dropdown.innerHTML = html;
          state.hasLoaded = true;
        })
        .catch(() => undefined);
    },
    isOpen: () => state.open && !dropdown.classList.contains("hidden"),
  };
})();

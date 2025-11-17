(function () {
  if (window.HubxPushInit) return;
  window.HubxPushInit = true;

  const formatCount = (count) => (count > 9 ? "9+" : String(count));

  let notificationCount = 0;

  const bellLink = document.querySelector("[data-notification-bell]");
  const getDropdownManager = () => window.HubxNotificationDropdown;

  if (bellLink) {
    notificationCount = parseInt(bellLink.dataset.notificationCount || "0", 10) || 0;
  }

  const isWebSocketSupported = "WebSocket" in window;

  const getLabelTemplate = (count) => {
    if (!bellLink) return "";
    const template = count === 1 ? bellLink.dataset.notificationLabelOne : bellLink.dataset.notificationLabelOther;
    return template ? template.replace("__count__", formatCount(count)) : "";
  };

  const notifyExternalUpdate = () => {
    window.HubxNotifications = {
      decrement: () => applyCount(Math.max(0, notificationCount - 1)),
      setCount: (value) => applyCount(Math.max(0, Number(value) || 0)),
    };
  };

  const applyCount = (count) => {
    notificationCount = count;
    const formatted = formatCount(notificationCount);
    const shouldHide = notificationCount <= 0;
    const targets = [document.getElementById("notif-count"), document.getElementById("push-notification-badge")];

    targets.forEach((el) => {
      if (!el) return;
      el.textContent = formatted;
      el.classList.toggle("hidden", shouldHide);
    });

    if (bellLink) {
      const label = getLabelTemplate(notificationCount);
      if (label) {
        bellLink.setAttribute("aria-label", label);
        bellLink.dataset.notificationCount = String(notificationCount);
      }
      const srText = bellLink.querySelector("[data-notification-sr]");
      if (srText && label) srText.textContent = label;
    }

    notifyExternalUpdate();
  };

  const refreshDropdownIfOpen = () => {
    const manager = getDropdownManager();
    if (!manager || typeof manager.refresh !== "function") return;
    if (typeof manager.isOpen === "function" && !manager.isOpen()) return;
    manager.refresh();
  };

  const RETRY_DELAY_MS = 5000;
  let reconnectTimer;
  let socket;

  const scheduleReconnect = () => {
    if (reconnectTimer) return;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, RETRY_DELAY_MS);
  };

    const connect = () => {
      if (document.body.dataset.isAuthenticated !== "true") return;
      if (!isWebSocketSupported) return;
      const scheme = window.location.protocol === "https:" ? "wss://" : "ws://";
    try {
      socket = new WebSocket(scheme + window.location.host + "/ws/notificacoes/");
    } catch (e) {
      console.warn("WebSocket desabilitado ou indisponível:", e);
      scheduleReconnect();
      return;
    }

    socket.onmessage = function (e) {
      const data = JSON.parse(e.data);
      if (data.event !== "notification_message") return;
      const nextCount = typeof data.total === "number" ? data.total : notificationCount + 1;
      applyCount(nextCount);
      refreshDropdownIfOpen();

      const container = document.getElementById("messages");
      const div = document.createElement("div");
      div.className = "px-4 py-2 rounded card bg-blue-500 text-white";
      div.setAttribute("role", "alert");
      div.setAttribute("aria-live", "assertive");
      div.textContent = (data.titulo ? data.titulo + ": " : "") + data.mensagem;
      (container || document.body).appendChild(div);
      setTimeout(() => div.remove(), 4000);
    };

    socket.onerror = function (event) {
      console.warn("Falha no WebSocket de notificações.", event);
      try {
        socket.close();
      } catch (err) {
        console.warn("Não foi possível fechar o WebSocket de notificações.", err);
      }
    };

    socket.onclose = function () {
      scheduleReconnect();
    };
  };

    document.addEventListener("DOMContentLoaded", () => {
      if (notificationCount > 0) applyCount(notificationCount);
      if (!isWebSocketSupported) {
        console.warn("WebSocket não suportado; mantendo atualização via fallback.");
        return;
      }
      connect();
    });
  })();

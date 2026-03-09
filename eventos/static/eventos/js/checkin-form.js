document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("checkin-form");
  if (!form) {
    return;
  }

  const codigoInput = document.getElementById("codigo");
  const feedback = document.getElementById("feedback");
  const readerEl = document.getElementById("reader");
  const submitButton = form.querySelector('button[type="submit"]');

  const successMessage = form.dataset.successMessage || "";
  const noCameraMessage = form.dataset.noCameraMessage || "";
  const cameraDeniedMessage = form.dataset.cameraDeniedMessage || "";
  const cameraErrorMessage = form.dataset.cameraErrorMessage || "";
  const checkinErrorMessage = form.dataset.checkinErrorMessage || "";

  const showCameraError = (error) => {
    const message = (error?.name === "NotAllowedError" || `${error}`.toLowerCase().includes("denied"))
      ? cameraDeniedMessage
      : cameraErrorMessage;

    feedback.classList.remove("text-[var(--success)]");
    feedback.classList.add("text-[var(--error)]");
    feedback.textContent = message;
    if (submitButton) {
      submitButton.disabled = false;
    }
  };

  const initQrScanner = () => {
    if (!window.Html5Qrcode || !readerEl || !codigoInput || !feedback) {
      return;
    }

    const qr = new Html5Qrcode("reader");

    const startWithCameraId = (cameraId) =>
      qr
        .start(
          cameraId,
          { fps: 10, qrbox: 250 },
          (decoded) => {
            codigoInput.value = decoded;
            qr.stop();
          },
          (err) => {
            showCameraError(err);
          }
        )
        .catch((err) => {
          showCameraError(err);
        });

    const startWithFacingMode = () =>
      qr
        .start(
          { facingMode: "environment" },
          { fps: 10, qrbox: 250 },
          (decoded) => {
            codigoInput.value = decoded;
            qr.stop();
          },
          (err) => {
            showCameraError(err);
          }
        )
        .catch((err) => {
          showCameraError(err);
        });

    const camerasPromise =
      typeof Html5Qrcode.getCameras === "function"
        ? Html5Qrcode.getCameras()
        : Promise.reject(new Error("getCameras not available"));

    camerasPromise
      .then((devices) => {
        if (!Array.isArray(devices) || devices.length === 0) {
          feedback.classList.remove("text-[var(--success)]");
          feedback.classList.add("text-[var(--error)]");
          feedback.textContent = noCameraMessage;
          return;
        }

        const preferredDevice =
          devices.find(
            (device) =>
              device?.facingMode === "environment" ||
              `${device?.label || ""}`.toLowerCase().includes("back") ||
              `${device?.label || ""}`.toLowerCase().includes("rear")
          ) || devices[0];

        startWithCameraId(preferredDevice.id);
      })
      .catch(() => {
        startWithFacingMode();
      });
  };

  if (window.Html5Qrcode) {
    initQrScanner();
  } else {
    document.addEventListener('html5-qrcode-ready', initQrScanner, { once: true });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    feedback.textContent = "";
    const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
    fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrf },
      body: new FormData(form),
    })
      .then((response) => {
        if (!response.ok) {
          return response.text().then((text) => {
            throw new Error(text || checkinErrorMessage);
          });
        }
        return response.json();
      })
      .then(() => {
        feedback.classList.remove("text-[var(--error)]");
        feedback.classList.add("text-[var(--success)]");
        feedback.textContent = successMessage;
        form.reset();
      })
      .catch((err) => {
        feedback.classList.remove("text-[var(--success)]");
        feedback.classList.add("text-[var(--error)]");
        feedback.textContent = err.message;
      });
  });
});

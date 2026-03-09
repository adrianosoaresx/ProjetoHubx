    (function () {
      function toggleSubmit() {
        const form = document.getElementById("tokenForm");
        if (!form) return;

        const submitButton = document.getElementById("submitButton");
        const tokenInput = document.getElementById("id_token");

        if (!submitButton) return;

        const tokenFilled = tokenInput && tokenInput.value.trim().length > 0;

        submitButton.disabled = !tokenFilled;
      }

      htmx.onLoad(function () {
        toggleSubmit();
        const tokenInput = document.getElementById("id_token");

        if (tokenInput) {
          tokenInput.addEventListener("input", toggleSubmit);
          tokenInput.addEventListener("blur", toggleSubmit);
        }
      });
    })();
  

        document.addEventListener("DOMContentLoaded", () => {
          const loginForm = document.querySelector("#login-form");
          const toggle = document.querySelector("#toggle-login-password");
          if (!loginForm || !toggle) {
            return;
          }
          const passwordInputs = Array.from(
            loginForm.querySelectorAll('input[type="password"]')
          );
          if (!passwordInputs.length) {
            return;
          }
          const updatePasswordVisibility = () => {
            const nextType = toggle.checked ? "text" : "password";
            passwordInputs.forEach((input) => {
              if (input.type !== nextType) {
                input.type = nextType;
              }
            });
          };
          toggle.addEventListener("change", updatePasswordVisibility);
        });
      

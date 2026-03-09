document.addEventListener('DOMContentLoaded', function () {
  const forms = document.querySelectorAll('[data-briefing-readonly-form="true"]');
  forms.forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
    });
  });
});

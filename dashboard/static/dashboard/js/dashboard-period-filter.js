document.addEventListener('DOMContentLoaded', function () {
  const selects = document.querySelectorAll('[data-dashboard-period-select]');
  selects.forEach(function (select) {
    select.addEventListener('change', function () {
      const form = select.form;
      if (form) {
        form.submit();
      }
    });
  });
});

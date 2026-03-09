document.addEventListener('DOMContentLoaded', function () {
  const loader = window.CdnScriptLoader;
  if (!loader || typeof loader.loadWithFallback !== 'function') {
    return;
  }

  loader
    .loadWithFallback(
      [
        '/static/js/vendor/html5-qrcode-2.3.8.min.js',
        'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
      ],
      {
        test: function () {
          return typeof window.Html5Qrcode !== 'undefined';
        },
      }
    )
    .finally(function () {
      document.dispatchEvent(new Event('html5-qrcode-ready'));
    });
});

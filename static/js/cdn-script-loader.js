(function () {
  function loadScript(url) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = url;
      script.defer = true;
      script.onload = function () {
        resolve(url);
      };
      script.onerror = function () {
        script.remove();
        reject(new Error('Falha ao carregar script: ' + url));
      };
      document.head.appendChild(script);
    });
  }

  function loadWithFallback(urls, options) {
    var queue = Array.isArray(urls) ? urls.filter(Boolean) : [];
    var settings = options || {};
    var test = typeof settings.test === 'function' ? settings.test : null;

    if (test && test()) {
      return Promise.resolve();
    }

    var index = 0;

    function next() {
      if (test && test()) {
        return Promise.resolve();
      }

      if (index >= queue.length) {
        return Promise.reject(new Error('Nenhuma URL de fallback disponível para o script solicitado.'));
      }

      var currentUrl = queue[index];
      index += 1;

      return loadScript(currentUrl).then(function () {
        if (test && !test()) {
          return next();
        }
        return undefined;
      }).catch(function () {
        return next();
      });
    }

    return next();
  }

  window.CdnScriptLoader = {
    loadWithFallback: loadWithFallback,
  };
})();

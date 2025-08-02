(function () {
  function scrollToBottom(list) {
    list.scrollTop = list.scrollHeight;
  }

  function init() {
    const form = document.getElementById('message-form');
    const list = document.getElementById('message-list');
    if (!form || !list) return;
    const channelId = form.dataset.channel;
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socketUrl = scheme + '://' + window.location.host + '/ws/chat/' + channelId + '/';
    let socket = new WebSocket(socketUrl);

    socket.onmessage = function (e) {
      const data = JSON.parse(e.data);
      if (!data.id) return;
      fetch('/chat/partials/message/' + data.id + '/')
        .then((r) => r.text())
        .then((html) => {
          list.insertAdjacentHTML('beforeend', html);
          scrollToBottom(list);
        });
    };

    socket.onclose = function () {
      setTimeout(init, 1000);
    };

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const tipo = form.querySelector('[name="tipo"]').value;
      const conteudo = form.querySelector('[name="conteudo"]').value.trim();
      if (socket.readyState === WebSocket.OPEN && tipo === 'text' && conteudo) {
        socket.send(JSON.stringify({ tipo: 'text', conteudo: conteudo }));
        form.reset();
      } else {
        form.submit();
      }
    });

    scrollToBottom(list);
  }

  document.addEventListener('DOMContentLoaded', init);
})();

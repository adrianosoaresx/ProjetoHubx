(function(){
    if(window.HubxPushInit) return;
    window.HubxPushInit = true;

    function init(){
        if(document.body.dataset.isAuthenticated !== 'true') return;
        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socket = new WebSocket(scheme + window.location.host + '/ws/notificacoes/');
        const countEl = document.getElementById('notif-count');
        socket.onmessage = function(e){
            const data = JSON.parse(e.data);
            if(countEl){
                const current = parseInt(countEl.textContent || '0', 10);
                countEl.textContent = current + 1;
            }
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'px-4 py-2 rounded shadow bg-blue-500 text-white';
            div.setAttribute('role','alert');
            div.setAttribute('aria-live','assertive');
            div.textContent = (data.titulo ? data.titulo + ': ' : '') + data.mensagem;
            (container || document.body).appendChild(div);
            setTimeout(()=>div.remove(),4000);
        };
    }
    document.addEventListener('DOMContentLoaded', init);
})();

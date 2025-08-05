(function(){
    function initCounter(elementId){
        const el = document.getElementById(elementId);
        if(!el) return;
        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const url = scheme + window.location.host + '/ws/chat/notificacoes/';
        const socket = new WebSocket(url);
        socket.onmessage = function(){
            const current = parseInt(el.textContent || '0', 10);
            el.textContent = current + 1;
        };
    }
    window.ChatNotifications = {initCounter};
})();

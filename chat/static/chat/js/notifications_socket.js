(function(){
    function getCsrfToken(){
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function init(){
        const btn = document.getElementById('notif-btn');
        const countEl = document.getElementById('notif-count');
        const listEl = document.getElementById('notif-list');
        const dropdown = document.getElementById('notif-dropdown');
        if(!btn || !countEl || !listEl || !dropdown) return;

        btn.addEventListener('click', ()=>{
            dropdown.classList.toggle('hidden');
            btn.setAttribute('aria-expanded', dropdown.classList.contains('hidden') ? 'false' : 'true');
        });

        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socket = new WebSocket(scheme + window.location.host + '/ws/chat/notificacoes/');

        function marcarLida(id){
            fetch('/api/chat/notificacoes/' + id + '/ler/', {
                method:'POST',
                headers:{'X-CSRFToken': getCsrfToken()},
            }).then(()=>{
                const current = parseInt(countEl.textContent || '0', 10);
                countEl.textContent = Math.max(0, current - 1);
            });
        }

        socket.onmessage = function(e){
            const data = JSON.parse(e.data);
            if(data.type !== 'chat.notification'){ return; }
            const current = parseInt(countEl.textContent || '0', 10);
            countEl.textContent = current + 1;
            const li = document.createElement('li');
            li.className = 'p-2 border-b';
            const link = document.createElement('a');
            link.href = data.canal_url || ('/chat/' + data.canal_id + '/');
            link.textContent = data.resumo || data.conteudo;
            link.className = 'block hover:bg-gray-100 focus:bg-gray-100';
            link.addEventListener('click', ()=>marcarLida(data.id));
            li.appendChild(link);
            listEl.prepend(li);
        };
    }

    document.addEventListener('DOMContentLoaded', init);
})();


(function(){
    if(window.HubxNotifInit) return;
    window.HubxNotifInit = true;

    function getCsrfToken(){
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    function playBeep(){
        try{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.1);
        }catch(e){/* noop */}
    }

    function init(){
        const btn = document.getElementById('notif-btn');
        const countEl = document.getElementById('notif-count');
        const listEl = document.getElementById('notif-list');
        const dropdown = document.getElementById('notif-dropdown');
        const soundChk = document.getElementById('notif-sound');
        const vibrateChk = document.getElementById('notif-vibrate');
        if(!btn || !countEl || !listEl || !dropdown) return;

        btn.addEventListener('click', ()=>{
            dropdown.classList.toggle('hidden');
            btn.setAttribute('aria-expanded', dropdown.classList.contains('hidden') ? 'false' : 'true');
        });

        const prefs = {
            sound: localStorage.getItem('notifSound') === '1',
            vibrate: localStorage.getItem('notifVibrate') === '1'
        };
        if(soundChk){
            soundChk.checked = prefs.sound;
            soundChk.addEventListener('change', ()=>{
                localStorage.setItem('notifSound', soundChk.checked ? '1' : '0');
            });
        }
        if(vibrateChk){
            vibrateChk.checked = prefs.vibrate;
            vibrateChk.addEventListener('change', ()=>{
                localStorage.setItem('notifVibrate', vibrateChk.checked ? '1' : '0');
            });
        }

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
            if(soundChk && soundChk.checked){ playBeep(); }
            if(vibrateChk && vibrateChk.checked && navigator.vibrate){ navigator.vibrate(200); }
        };
    }

    document.addEventListener('DOMContentLoaded', init);
})();


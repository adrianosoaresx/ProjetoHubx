(function(){
    function init(container){
        if(!container) return;
        const destinatarioId = container.dataset.destId;
        const currentUser = container.dataset.currentUser;
        const csrfToken = container.dataset.csrfToken;
        const uploadUrl = container.dataset.uploadUrl || '';
        if(container._chatSocket){
            try { container._chatSocket.close(); } catch(err){}
        }
        const chatSocket = new WebSocket(
            (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
            window.location.host +
            '/ws/chat/' + destinatarioId + '/'
        );
        container._chatSocket = chatSocket;

        const messages = container.querySelector('#chat-messages');
        const input = container.querySelector('#chat-input');
        const form = container.querySelector('#chat-form');
        const fileInput = container.querySelector('#file-input');
        const uploadBtn = container.querySelector('#upload-btn');

        function scrollToBottom(){
            messages.scrollTop = messages.scrollHeight;
        }

        const pending = [];

        function renderMessage(remetente, tipo, conteudo, elem){
            const div = elem || document.createElement('div');
            div.classList.add('message');
            if(remetente === currentUser){
                div.classList.add('self');
            }
            let content = conteudo;
            if(tipo === 'image'){
                content = `<img src="${conteudo}" alt="imagem" class="chat-media-thumb">`;
            } else if(tipo === 'video'){
                content = `<video src="${conteudo}" controls class="chat-media-thumb"></video>`;
            } else if(tipo === 'file'){
                content = `<div class="chat-file">
        <a href="${conteudo}" target="_blank">📎 Baixar arquivo</a>
    </div>`;
            }
            div.innerHTML = '<strong>' + remetente + '</strong>: ' + content;
            return div;
        }

        chatSocket.onmessage = function(e){
            const data = JSON.parse(e.data);
            // Remove pending placeholder if it matches the incoming data
            if(data.remetente === currentUser){
                const idx = pending.findIndex(p => p.tipo === data.tipo && p.conteudo === data.conteudo);
                if(idx !== -1){
                    const placeholder = pending[idx];
                    renderMessage(data.remetente, data.tipo, data.conteudo, placeholder.elem);
                    placeholder.elem.classList.remove('pending');
                    pending.splice(idx,1);
                    scrollToBottom();
                    return;
                }
            }
            const div = renderMessage(data.remetente, data.tipo, data.conteudo);
            messages.appendChild(div);
            scrollToBottom();
        };

        form.addEventListener('submit', function(e){
            e.preventDefault();
            const message = input.value.trim();
            if(message){
                const div = renderMessage(currentUser, 'text', message);
                div.classList.add('pending');
                messages.appendChild(div);
                pending.push({tipo: 'text', conteudo: message, elem: div});
                scrollToBottom();
                chatSocket.send(JSON.stringify({tipo:'text', conteudo: message}));
                input.value = '';
            }
        });

        uploadBtn.addEventListener('click', function(){ fileInput.click(); });
        fileInput.addEventListener('change', function(){
            const file = fileInput.files[0];
            if(!file) return;
            const formData = new FormData();
            formData.append('file', file);
            fetch(uploadUrl, {method:'POST', body: formData, headers:{'X-CSRFToken': csrfToken}})
                .then(r => r.json())
                .then(data => {
                    const div = renderMessage(currentUser, data.tipo, data.url);
                    div.classList.add('pending');
                    messages.appendChild(div);
                    pending.push({tipo: data.tipo, conteudo: data.url, elem: div});
                    scrollToBottom();
                    chatSocket.send(JSON.stringify({tipo: data.tipo, conteudo: data.url}));
                });
        });

        scrollToBottom();
    }
    window.HubXChatRoom = {init};
})();

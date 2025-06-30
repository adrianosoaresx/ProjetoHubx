(function(){
    function init(container){
        if(!container) return;
        const destId = container.dataset.destId;
        const currentUser = container.dataset.currentUser;
        const csrfToken = container.dataset.csrfToken;
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const socket = new WebSocket(`${scheme}://${window.location.host}/ws/chat/${destId}/`);

        const messages = container.querySelector('#chat-messages');
        const input = container.querySelector('#chat-input');
        const form = container.querySelector('#chat-form');
        const fileInput = container.querySelector('#file-input');
        const uploadBtn = container.querySelector('#upload-btn');

        function scrollToBottom(){
            messages.scrollTop = messages.scrollHeight;
        }

        socket.onmessage = function(e){
            const data = JSON.parse(e.data);
            const div = document.createElement('div');
            div.classList.add('message');
            if(data.remetente === currentUser){
                div.classList.add('self');
            }
            let content = data.conteudo;
            if(data.tipo === 'image'){
                content = `<img src="${data.conteudo}" alt="imagem" class="chat-media">`;
            } else if(data.tipo === 'video'){
                content = `<video src="${data.conteudo}" controls class="chat-media"></video>`;
            } else if(data.tipo === 'file'){
                content = `<a href="${data.conteudo}" target="_blank">Baixar arquivo</a>`;
            }
            div.innerHTML = '<strong>' + data.remetente + '</strong>: ' + content;
            messages.appendChild(div);
            scrollToBottom();
        };

        form.addEventListener('submit', function(e){
            e.preventDefault();
            const message = input.value.trim();
            if(message){
                socket.send(JSON.stringify({tipo:'text', conteudo: message}));
                input.value = '';
            }
        });

        uploadBtn.addEventListener('click', function(){ fileInput.click(); });
        fileInput.addEventListener('change', function(){
            const file = fileInput.files[0];
            if(!file) return;
            const formData = new FormData();
            formData.append('file', file);
            fetch('', {method:'POST', body: formData, headers:{'X-CSRFToken': csrfToken}})
                .then(r => r.json())
                .then(data => {
                    socket.send(JSON.stringify({tipo: data.tipo, conteudo: data.url}));
                });
        });

        scrollToBottom();
    }
    window.HubXChatRoom = {init};
})();

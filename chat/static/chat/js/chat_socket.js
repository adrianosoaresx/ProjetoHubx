(function(){
    function createSocket(container, url){
        let socket;
        function connect(){
            socket = new WebSocket(url);
            container._chatSocket = socket;
            socket.onclose = function(){
                if(!container._closing){
                    setTimeout(connect, 1000);
                }
            };
        }
        connect();
        return ()=>{ container._closing = true; socket.close(); };
    }

    function init(container){
        if(!container) return;
        const destinatarioId = container.dataset.destId;
        const currentUser = container.dataset.currentUser;
        const csrfToken = container.dataset.csrfToken;
        const isAdmin = container.dataset.isAdmin === 'true';
        const uploadUrl = container.dataset.uploadUrl || '';
        const historyUrl = container.dataset.historyUrl || '';
        const scheme = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const hostname = window.location.hostname;
        const url = scheme + hostname + ':8001/ws/chat/' + destinatarioId + '/';

        if(container._chatCleanup){ container._chatCleanup(); }
        const closeSocket = createSocket(container, url);
        container._chatCleanup = closeSocket;
        const chatSocket = container._chatSocket;

        const messages = container.querySelector('#chat-messages');
        const input = container.querySelector('#chat-input');
        const form = container.querySelector('#chat-form');
        const fileInput = container.querySelector('#file-input');
        const uploadBtn = container.querySelector('#upload-btn');

        function renderReactions(div, reactions){
            const list = div.querySelector('.reactions');
            if(!list) return;
            list.innerHTML = '';
            if(reactions){
                Object.entries(reactions).forEach(([emoji,count])=>{
                    const li = document.createElement('li');
                    li.className = 'text-sm';
                    li.textContent = `${emoji} ${count}`;
                    list.appendChild(li);
                });
            }
        }

        function setupReactionMenu(div, id){
            const menu = div.querySelector('.reaction-menu');
            if(!menu || !id) return;
            div.addEventListener('mouseenter', ()=>menu.classList.remove('hidden'));
            div.addEventListener('mouseleave', ()=>menu.classList.add('hidden'));
            menu.addEventListener('click', e=>{
                const btn = e.target.closest('.react-option');
                if(!btn) return;
                const emoji = btn.dataset.emoji;
                fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/react/`,{
                    method:'POST',
                    headers:{'X-CSRFToken':csrfToken,'Content-Type':'application/json'},
                    body: JSON.stringify({emoji})
                });
                menu.classList.add('hidden');
            });
        }

        function scrollToBottom(){ messages.scrollTop = messages.scrollHeight; }
        const pending = [];

        messages.querySelectorAll('[data-message-id]').forEach(el=>{
            setupReactionMenu(el, el.dataset.messageId);
        });
        const pinned = container.querySelector('#pinned');
        if(pinned){
            pinned.querySelectorAll('[data-message-id]').forEach(el=>{
                setupReactionMenu(el, el.dataset.messageId);
            });
        }

        if(historyUrl){
            fetch(historyUrl).then(r=>r.json()).then(data=>{
                data.messages.forEach(m=>{
                    const div = renderMessage(m.remetente, m.tipo, m.conteudo, null, m.id, m.pinned_at, m.reactions);
                    messages.appendChild(div);
                });
                scrollToBottom();
            });
        }

        function renderMessage(remetente,tipo,conteudo,elem,id,pinned,reactions){
            const div = elem || document.createElement('article');
            div.className = 'message relative p-2';
            if(remetente === currentUser){ div.classList.add('self'); }
            if(pinned){ div.classList.add('pinned'); }
            let content = conteudo;
            if(tipo === 'image'){
                content = `<img src="${conteudo}" alt="imagem" class="chat-media-thumb">`;
            }else if(tipo === 'video'){
                content = `<video src="${conteudo}" controls class="chat-media-thumb"></video>`;
            }else if(tipo === 'file'){
                content = `<div class="chat-file"><a href="${conteudo}" target="_blank">📎 Baixar arquivo</a></div>`;
            }
            div.innerHTML = `<div><strong>${remetente}</strong>: ${content}</div><ul class="reactions flex gap-2 ml-2"></ul><div class="reaction-menu hidden absolute bg-white border rounded p-1 flex gap-1" role="menu"><button type="button" class="react-option" data-emoji="👍" aria-label="Adicionar reação 👍">👍</button><button type="button" class="react-option" data-emoji="😂" aria-label="Adicionar reação 😂">😂</button><button type="button" class="react-option" data-emoji="❤️" aria-label="Adicionar reação ❤️">❤️</button><button type="button" class="react-option" data-emoji="😮" aria-label="Adicionar reação 😮">😮</button></div>`;
            if(id){ div.dataset.id = id; }
            if(isAdmin && id){
                const btn = document.createElement('button');
                btn.classList.add('pin-toggle');
                btn.textContent = pinned ? 'Desafixar' : 'Fixar';
                btn.setAttribute('aria-label', pinned ? 'Desafixar mensagem' : 'Fixar mensagem');
                btn.addEventListener('click', ()=>{
                    const action = div.classList.contains('pinned') ? 'unpin' : 'pin';
                    fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/${action}/`,{method:'POST',headers:{'X-CSRFToken':csrfToken}})
                        .then(r=>r.json()).then(data=>{
                            div.classList.toggle('pinned', !!data.pinned_at);
                            btn.textContent = data.pinned_at ? 'Desafixar' : 'Fixar';
                            btn.setAttribute('aria-label', data.pinned_at ? 'Desafixar mensagem' : 'Fixar mensagem');
                        });
                });
                div.appendChild(btn);
            }
            if(id && (remetente === currentUser || isAdmin) && tipo === 'text'){
                const edit = document.createElement('button');
                edit.className = 'edit-msg ml-2 text-xs text-blue-600';
                edit.textContent = 'Editar';
                edit.setAttribute('aria-label','Editar mensagem');
                edit.addEventListener('click', ()=>{
                    const novo = prompt('Editar mensagem', conteudo);
                    if(!novo || novo === conteudo) return;
                    fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/`,{
                        method:'PATCH',
                        headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},
                        body: JSON.stringify({conteudo: novo})
                    }).then(r=>r.ok?r.json():Promise.reject())
                      .then(data=>{
                        renderMessage(data.remetente, data.tipo, data.conteudo, div, data.id, data.pinned_at, data.reactions);
                      });
                });
                div.appendChild(edit);
            }
            renderReactions(div,reactions);
            setupReactionMenu(div,id);
            return div;
        }

        chatSocket.onmessage = function(e){
            const data = JSON.parse(e.data);
            if(data.remetente === currentUser){
                const idx = pending.findIndex(p=>p.tipo===data.tipo && p.conteudo===data.conteudo);
                if(idx!==-1){
                    const placeholder = pending[idx];
                    renderMessage(data.remetente, data.tipo, data.conteudo, placeholder.elem, data.id, data.pinned_at, data.reactions);
                    placeholder.elem.classList.remove('pending');
                    pending.splice(idx,1);
                    scrollToBottom();
                    return;
                }
            }
            const existing = messages.querySelector(`[data-id="${data.id}"]`);
            const div = renderMessage(data.remetente, data.tipo, data.conteudo, existing, data.id, data.pinned_at, data.reactions);
            if(!existing){
                messages.appendChild(div);
                scrollToBottom();
            }
        };

        form.addEventListener('submit', function(e){
            e.preventDefault();
            const message = input.value.trim();
            if(message){
                const div = renderMessage(currentUser, 'text', message, null, null, false, {});
                div.classList.add('pending');
                messages.appendChild(div);
                pending.push({tipo:'text', conteudo:message, elem:div});
                scrollToBottom();
                chatSocket.send(JSON.stringify({tipo:'text', conteudo:message}));
                input.value = '';
            }
        });

        uploadBtn.addEventListener('click', ()=> fileInput.click());
        fileInput.addEventListener('change', function(){
            const file = fileInput.files[0];
            if(!file) return;
            uploadBtn.disabled = true;
            const spin = document.createElement('span');
            spin.className = 'ml-2 animate-spin';
            spin.textContent = '⏳';
            uploadBtn.appendChild(spin);
            const formData = new FormData();
            formData.append('file', file);
            fetch(uploadUrl,{method:'POST',body:formData,headers:{'X-CSRFToken':csrfToken}})
                .then(r=>{ if(!r.ok) throw new Error(); return r.json(); })
                .then(data=>{
                    const div = renderMessage(currentUser,data.tipo,data.url,null,null,false,{});
                    div.classList.add('pending');
                    messages.appendChild(div);
                    pending.push({tipo:data.tipo,conteudo:data.url,elem:div});
                    scrollToBottom();
                    chatSocket.send(JSON.stringify({tipo:data.tipo, conteudo:data.url}));
                })
                .catch(()=>{ alert('Erro no upload'); })
                .finally(()=>{
                    uploadBtn.disabled = false;
                    spin.remove();
                    fileInput.value = '';
                });
        });

        scrollToBottom();
    }

    window.HubXChatRoom = {init};
})();

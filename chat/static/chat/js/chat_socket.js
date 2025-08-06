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
        const editModal = document.getElementById('edit-modal');
        const editInput = editModal ? editModal.querySelector('#edit-input') : null;
        const editCancel = editModal ? editModal.querySelector('#edit-cancel') : null;
        const editForm = editModal ? editModal.querySelector('form') : null;
        let editState = {id:null, div:null, original:''};
        let oldestId = null;
        let historyEnd = false;
        let historyLoading = false;

        if(editCancel){
            editCancel.addEventListener('click', ()=> editModal.close());
        }

        function openEditModal(div,id,content){
            if(!editModal || !editInput) return;
            editState = {id, div, original: content};
            editInput.value = content;
            editModal.showModal();
            editInput.focus();
        }

        if(editForm && editInput){
            editForm.addEventListener('submit', function(e){
                e.preventDefault();
                const novo = editInput.value.trim();
                if(!novo || novo === editState.original){ editModal.close(); return; }
                fetch(`/api/chat/channels/${destinatarioId}/messages/${editState.id}/`,{
                    method:'PATCH',
                    headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},
                    body: JSON.stringify({conteudo: novo})
                }).then(r=>r.ok?r.json():Promise.reject())
                  .then(data=>{
                    renderMessage(data.remetente, data.tipo, data.conteudo, editState.div, data.id, data.pinned_at, data.reactions, data.user_reactions);
                  })
                  .finally(()=> editModal.close());
            });
            editInput.addEventListener('keydown', function(e){
                if((e.ctrlKey || e.metaKey) && e.key === 'Enter'){
                    editForm.requestSubmit();
                }
            });
        }

        const texts = window.chatTexts || {};
        function t(key, fallback){ return texts[key] || fallback; }

        function renderReactions(div, reactions, userReactions){
            const list = div.querySelector('.reactions');
            if(!list) return;
            list.innerHTML = '';
            if(reactions){
                Object.entries(reactions).forEach(([emoji,count])=>{
                    const li = document.createElement('li');
                    li.className = 'text-sm';
                    li.dataset.emoji = emoji;
                    if(userReactions && userReactions.includes(emoji)){
                        li.classList.add('font-bold');
                    }
                    li.textContent = `${emoji} ${count}`;
                    list.appendChild(li);
                });
            }
        }

        function setupReactionMenu(div, id){
            const btn = div.querySelector('.reaction-btn');
            const menu = div.querySelector('.reaction-menu');
            const list = div.querySelector('.reactions');
            if(!btn || !menu || !id) return;
            function closeMenu(){
                menu.classList.add('hidden');
                btn.setAttribute('aria-expanded','false');
            }
            btn.addEventListener('click', ()=>{
                const hidden = menu.classList.toggle('hidden');
                if(!hidden){
                    btn.setAttribute('aria-expanded','true');
                    const first = menu.querySelector('button');
                    if(first){ first.focus(); }
                }else{
                    btn.setAttribute('aria-expanded','false');
                }
            });
            menu.addEventListener('keydown', e=>{
                const opts = Array.from(menu.querySelectorAll('.react-option'));
                const idx = opts.indexOf(document.activeElement);
                if(e.key === 'ArrowRight' || e.key === 'ArrowDown'){
                    e.preventDefault();
                    const next = opts[(idx + 1) % opts.length];
                    next && next.focus();
                } else if(e.key === 'ArrowLeft' || e.key === 'ArrowUp'){
                    e.preventDefault();
                    const prev = opts[(idx - 1 + opts.length) % opts.length];
                    prev && prev.focus();
                } else if(e.key === 'Escape'){
                    e.preventDefault();
                    closeMenu();
                    btn.focus();
                }
            });
            menu.addEventListener('click', e=>{
                const opt = e.target.closest('.react-option');
                if(!opt) return;
                const emoji = opt.dataset.emoji;
                fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/react/`,{
                    method:'POST',
                    headers:{'X-CSRFToken':csrfToken,'Content-Type':'application/json'},
                    body: JSON.stringify({emoji})
                }).then(r=>r.ok?r.json():Promise.reject())
                  .then(data=>{
                    renderReactions(div, data.reactions, data.user_reactions);
                  });
                closeMenu();
            });
            if(list){
                list.addEventListener('click', e=>{
                    const li = e.target.closest('li');
                    if(!li) return;
                    const emoji = li.dataset.emoji;
                    fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/react/`,{
                        method:'POST',
                        headers:{'X-CSRFToken':csrfToken,'Content-Type':'application/json'},
                        body: JSON.stringify({emoji})
                    }).then(r=>r.ok?r.json():Promise.reject())
                      .then(data=>{
                        renderReactions(div, data.reactions, data.user_reactions);
                      });
                });
            }
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
                const frag = document.createDocumentFragment();
                const ordered = data.messages.slice().reverse();
                ordered.forEach(m=>{
                    const div = renderMessage(m.remetente, m.tipo, m.conteudo, null, m.id, m.pinned_at, m.reactions, m.user_reactions);
                    frag.appendChild(div);
                });
                messages.appendChild(frag);
                if(ordered.length){
                    oldestId = ordered[0].id;
                }
                historyEnd = !data.has_more;
                scrollToBottom();
            });
        }

        function loadPrevious(){
            if(historyLoading || historyEnd || !historyUrl) return;
            historyLoading = true;
            const url = new URL(historyUrl, window.location.origin);
            if(oldestId){ url.searchParams.set('before', oldestId); }
            fetch(url).then(r=>r.json()).then(data=>{
                if(data.messages.length){
                    const first = messages.firstChild;
                    const prevHeight = messages.scrollHeight;
                    const frag = document.createDocumentFragment();
                    const ordered = data.messages.slice().reverse();
                    ordered.forEach(m=>{
                        const div = renderMessage(m.remetente, m.tipo, m.conteudo, null, m.id, m.pinned_at, m.reactions, m.user_reactions);
                        frag.appendChild(div);
                    });
                    messages.insertBefore(frag, first);
                    oldestId = ordered[0].id;
                    const newHeight = messages.scrollHeight;
                    messages.scrollTop = newHeight - prevHeight;
                }else{
                    historyEnd = true;
                }
                if(!data.has_more){ historyEnd = true; }
            }).finally(()=>{ historyLoading = false; });
        }

        messages.addEventListener('scroll', ()=>{
            if(messages.scrollTop < 50){
                loadPrevious();
            }
        });

        function renderMessage(remetente,tipo,conteudo,elem,id,pinned,reactions,userReactions){
            const div = elem || document.createElement('article');
            div.className = 'message relative p-2';
            if(remetente === currentUser){ div.classList.add('self'); }
            if(pinned){ div.classList.add('pinned'); }
            let content = conteudo;
            if(tipo === 'image'){
                content = `<img src="${conteudo}" alt="imagem" class="w-full max-w-xs h-auto rounded">`;
            }else if(tipo === 'video'){
                content = `<video src="${conteudo}" controls class="w-full max-w-xs h-auto" aria-label="${t('videoPlayer','Player de vídeo')}"></video>`;
            }else if(tipo === 'file'){
                content = `<div class="chat-file"><a href="${conteudo}" target="_blank">📎 Baixar arquivo</a></div>`;
            }
            div.innerHTML = `<div><strong>${remetente}</strong>: ${content}</div><ul class="reactions flex gap-2 ml-2"></ul><div class="reaction-container relative"><button type="button" class="reaction-btn" aria-haspopup="true" aria-expanded="false" aria-label="${t('addReaction','Adicionar reação')}">🙂</button><ul class="reaction-menu hidden absolute bg-white border rounded p-1 flex gap-1" role="menu"><li><button type="button" class="react-option" data-emoji="🙂" aria-label="${t('reactWith','Reagir com')} 🙂">🙂</button></li><li><button type="button" class="react-option" data-emoji="❤️" aria-label="${t('reactWith','Reagir com')} ❤️">❤️</button></li><li><button type="button" class="react-option" data-emoji="👍" aria-label="${t('reactWith','Reagir com')} 👍">👍</button></li><li><button type="button" class="react-option" data-emoji="😂" aria-label="${t('reactWith','Reagir com')} 😂">😂</button></li><li><button type="button" class="react-option" data-emoji="🎉" aria-label="${t('reactWith','Reagir com')} 🎉">🎉</button></li><li><button type="button" class="react-option" data-emoji="😢" aria-label="${t('reactWith','Reagir com')} 😢">😢</button></li><li><button type="button" class="react-option" data-emoji="😡" aria-label="${t('reactWith','Reagir com')} 😡">😡</button></li></ul></div>`;
            if(id){ div.dataset.id = id; div.dataset.messageId = id; }
            if(isAdmin && id){
                const btn = document.createElement('button');
                btn.classList.add('pin-toggle');
                btn.textContent = pinned ? t('unpin','Desafixar') : t('pin','Fixar');
                btn.setAttribute('aria-label', pinned ? t('unpinMessage','Desafixar mensagem') : t('pinMessage','Fixar mensagem'));
                btn.addEventListener('click', ()=>{
                    const action = div.classList.contains('pinned') ? 'unpin' : 'pin';
                    fetch(`/api/chat/channels/${destinatarioId}/messages/${id}/${action}/`,{method:'POST',headers:{'X-CSRFToken':csrfToken}})
                        .then(r=>r.json()).then(data=>{
                            div.classList.toggle('pinned', !!data.pinned_at);
                            btn.textContent = data.pinned_at ? t('unpin','Desafixar') : t('pin','Fixar');
                            btn.setAttribute('aria-label', data.pinned_at ? t('unpinMessage','Desafixar mensagem') : t('pinMessage','Fixar mensagem'));
                        });
                });
                div.appendChild(btn);
            }
            if(id && (remetente === currentUser || isAdmin) && tipo === 'text'){
                const edit = document.createElement('button');
                edit.className = 'edit-msg ml-2 text-xs text-blue-600';
                edit.textContent = t('edit','Editar');
                edit.setAttribute('aria-label', t('edit','Editar mensagem'));
                edit.addEventListener('click', ()=>{
                    openEditModal(div, id, conteudo);
                });
                div.appendChild(edit);
            }
            renderReactions(div,reactions,userReactions);
            setupReactionMenu(div,id);
            return div;
        }

        chatSocket.onmessage = function(e){
            const data = JSON.parse(e.data);
            if(data.remetente === currentUser){
                const idx = pending.findIndex(p=>p.tipo===data.tipo && p.conteudo===data.conteudo);
                if(idx!==-1){
                    const placeholder = pending[idx];
                    renderMessage(data.remetente, data.tipo, data.conteudo, placeholder.elem, data.id, data.pinned_at, data.reactions, data.user_reactions);
                    placeholder.elem.classList.remove('pending');
                    pending.splice(idx,1);
                    scrollToBottom();
                    return;
                }
            }
            const existing = messages.querySelector(`[data-id="${data.id}"]`);
            let userReactions = [];
            if(existing){
                userReactions = Array.from(existing.querySelectorAll('.reactions li.font-bold')).map(li=>li.textContent.split(' ')[0]);
            }
            if(data.actor && data.actor === currentUser){
                userReactions = data.user_reactions || [];
            }
            const div = renderMessage(data.remetente, data.tipo, data.conteudo, existing, data.id, data.pinned_at, data.reactions, userReactions);
            if(!existing){
                messages.appendChild(div);
                scrollToBottom();
            }
        };

        form.addEventListener('submit', function(e){
            e.preventDefault();
            const message = input.value.trim();
            if(message){
                const div = renderMessage(currentUser, 'text', message, null, null, false, {}, []);
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
                    const div = renderMessage(currentUser,data.tipo,data.url,null,null,false,{}, []);
                    div.classList.add('pending');
                    messages.appendChild(div);
                    pending.push({tipo:data.tipo,conteudo:data.url,elem:div});
                    scrollToBottom();
                    chatSocket.send(JSON.stringify({tipo:data.tipo, conteudo:data.url}));
                })
                .catch(()=>{ alert(t('uploadError','Erro no upload')); })
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

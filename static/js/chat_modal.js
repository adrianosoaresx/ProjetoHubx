// Chat floating window logic for HubX

document.addEventListener('DOMContentLoaded', () => {
    const chatLink = document.getElementById('chat-link');
    const container = document.getElementById('chat-float-container');
    const usersUrl = '/chat/modal/users/';
    const roomUrlBase = '/chat/modal/room/';

    function executeScripts(el) {
        el.querySelectorAll('script').forEach(oldScript => {
            const newScript = document.createElement('script');
            newScript.textContent = oldScript.textContent;
            document.body.appendChild(newScript);
            document.body.removeChild(newScript);
        });
    }

    function closeCurrentSocket() {
        const chatEl = container.querySelector('#chat-container');
        if (chatEl && chatEl._chatSocket) {
            try { chatEl._chatSocket.close(); } catch (e) {}
        }
    }

    function openUserList() {
        closeCurrentSocket();
        fetch(usersUrl)
            .then(r => r.text())
            .then(html => {
                container.innerHTML = html;
                container.classList.remove('hidden');
                executeScripts(container);
            });
    }

    function bindBackButton() {
        const back = document.getElementById('backToUsers');
        if (back) {
            back.addEventListener('click', e => {
                e.preventDefault();
                openUserList();
            });
        }
    }

    function abrirChat(userId) {
        const url = `${roomUrlBase}${userId}/`;
        closeCurrentSocket();
        fetch(url)
            .then(r => r.text())
            .then(html => {
                container.innerHTML = html;
                container.classList.remove('hidden');
                executeScripts(container);
                bindBackButton();
                if (window.HubXChatRoom) {
                    const chatContainer = container.querySelector('#chat-container');
                    HubXChatRoom.init(chatContainer);
                }
                const chatMessages = container.querySelector('#chat-messages');
                if (chatMessages) {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            });
    }

    function fecharChat() {
        closeCurrentSocket();
        container.classList.add('hidden');
        container.innerHTML = '';
    }

    if (chatLink) {
        chatLink.addEventListener('click', e => {
            e.preventDefault();
            openUserList();
        });
    }

    window.abrirChat = abrirChat;
    window.fecharChat = fecharChat;
});

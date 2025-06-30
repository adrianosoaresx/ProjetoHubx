// Chat modal logic for HubX

document.addEventListener('DOMContentLoaded', () => {
    const chatLink = document.getElementById('chat-link');
    const chatButtons = document.querySelectorAll('.chat-open');
    const modal = document.getElementById('chatModal');
    const modalBody = document.getElementById('chatModalBody');
    const modalTitle = document.getElementById('chatModalTitle');
    const closeBtn = document.getElementById('closeChatModal');

    if (chatLink) {
        chatLink.addEventListener('click', (e) => {
            e.preventDefault();
            openUserList();
        });
    }
    chatButtons.forEach((btn) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const uid = btn.dataset.id;
            if (uid) openChatRoom(uid);
        });
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    function openModal() {
        modal.classList.add('active');
    }

    function closeModal() {
        modal.classList.remove('active');
        modalBody.innerHTML = '';
    }

    function executeScripts(container) {
        container.querySelectorAll('script').forEach((oldScript) => {
            const newScript = document.createElement('script');
            newScript.textContent = oldScript.textContent;
            document.body.appendChild(newScript);
            document.body.removeChild(newScript);
        });
    }

    function bindUserCards() {
        modalBody.querySelectorAll('.connection-card').forEach((card) => {
            card.addEventListener('click', () => openChatRoom(card.dataset.id));
        });
    }

    function openUserList() {
        fetch('/chat/modal/users/')
            .then((r) => r.text())
            .then((html) => {
                modalBody.innerHTML = html;
                modalTitle.textContent = 'Chat';
                openModal();
                executeScripts(modalBody);
                bindUserCards();
            });
    }

    function bindBackButton() {
        const back = document.getElementById('backToUsers');
        if (back) {
            back.addEventListener('click', (e) => {
                e.preventDefault();
                openUserList();
            });
        }
    }

    function openChatRoom(userId) {
        fetch(`/chat/modal/room/${userId}/`)
            .then((r) => r.text())
            .then((html) => {
                modalBody.innerHTML = html;
                modalTitle.textContent = 'Bate-papo';
                openModal();
                bindBackButton();
                if (window.HubXChatRoom) {
                    HubXChatRoom.init(modalBody);
                }
            });
    }

    window.HubXChat = { openUserList, openChatRoom };
});

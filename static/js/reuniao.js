(function () {
    const app = document.getElementById('reuniao-app');
    const salaSelect = document.getElementById('sala-select');
    const jitsiFrame = document.getElementById('jitsi-frame');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');

    if (!app) return;

    let sala = app.dataset.sala;
    let lastId = 0;
    let pollTimer = null;

    chatMessages.querySelectorAll('.chat-msg').forEach(() => {});

    function getCsrfToken() {
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function scrollChat() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendMessage(msg) {
        if (msg.id <= lastId) return;
        lastId = Math.max(lastId, msg.id);

        const div = document.createElement('div');
        div.className = 'chat-msg' + (msg.eu ? ' eu' : '');
        div.dataset.id = msg.id;
        div.innerHTML = `
            <div class="chat-meta">
                <strong>${escapeHtml(msg.autor)}</strong>
                <span>${msg.hora}</span>
            </div>
            <p>${escapeHtml(msg.texto)}</p>`;
        chatMessages.appendChild(div);
        scrollChat();
    }

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function initLastId() {
        chatMessages.querySelectorAll('.chat-msg[data-id]').forEach((el) => {
            const id = parseInt(el.dataset.id, 10);
            if (!isNaN(id)) lastId = Math.max(lastId, id);
        });
    }

    async function pollMessages() {
        try {
            const res = await fetch(`/api/reuniao/mensagens/?sala=${encodeURIComponent(sala)}&since=${lastId}`);
            if (!res.ok) return;
            const data = await res.json();
            data.mensagens.forEach(appendMessage);
        } catch {
            /* silencioso — reconecta no próximo poll */
        }
    }

    async function sendMessage(texto) {
        const res = await fetch('/api/reuniao/enviar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ sala, texto }),
        });
        const data = await res.json();
        if (res.ok) {
            appendMessage(data);
        }
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const texto = chatInput.value.trim();
        if (!texto) return;
        chatInput.value = '';
        chatInput.disabled = true;
        try {
            await sendMessage(texto);
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    });

    if (salaSelect) {
        salaSelect.addEventListener('change', () => {
            const slug = salaSelect.value;
            window.location.href = '/reuniao/?sala=' + encodeURIComponent(slug);
        });
    }

    initLastId();
    pollMessages();
    pollTimer = setInterval(pollMessages, 3000);
    scrollChat();

    window.addEventListener('beforeunload', () => {
        if (pollTimer) clearInterval(pollTimer);
    });
})();

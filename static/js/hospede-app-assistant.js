(function () {
    'use strict';

    var fab = document.getElementById('app-assistant-fab');
    var panel = document.getElementById('app-assistant-panel');
    var closeBtn = document.getElementById('app-assistant-close');
    var messages = document.getElementById('app-assistant-messages');
    var suggestions = document.getElementById('app-assistant-suggestions');
    var form = document.getElementById('app-assistant-form');
    var input = document.getElementById('app-assistant-input');
    if (!fab || !panel || !form) return;

    var INIT_URL = '/app/assistente/init/';
    var CHAT_URL = '/app/assistente/chat/';
    var history = [];
    var iniciado = false;

    function csrf() {
        var el = form.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function render(texto) {
        return texto
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }

    function addMsg(texto, autor) {
        var div = document.createElement('div');
        div.className = 'app-assistant-msg app-assistant-msg-' + autor;
        div.innerHTML = render(texto);
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    function setSuggestions(lista) {
        suggestions.innerHTML = '';
        (lista || []).forEach(function (s) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'app-assistant-chip';
            b.textContent = s;
            b.addEventListener('click', function () { enviar(s); });
            suggestions.appendChild(b);
        });
    }

    var SAUDACAO_PADRAO = 'Oi! ✨ Sou a Recrear, sua guia aqui no app. Posso te contar a programação de hoje, os passeios, como pagar via PIX e a noite temática. O que você quer saber?';
    var SUGESTOES_PADRAO = [
        'Qual a programação de hoje?',
        'Quais passeios têm hoje?',
        'Como pago o passeio pelo PIX?',
        'Qual a noite temática de hoje?',
    ];

    function init() {
        if (iniciado) return;
        iniciado = true;
        var saudacaoEl = addMsg(SAUDACAO_PADRAO, 'bot');
        setSuggestions(SUGESTOES_PADRAO);
        fetch(INIT_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) {
                if (!r.ok) throw new Error('init ' + r.status);
                return r.json();
            })
            .then(function (data) {
                if (data.greeting) saudacaoEl.innerHTML = render(data.greeting);
                if (data.suggestions && data.suggestions.length) setSuggestions(data.suggestions);
            })
            .catch(function () { /* mantém saudação padrão */ });
    }

    function enviar(texto) {
        texto = (texto || '').trim();
        if (!texto) return;
        addMsg(texto, 'user');
        history.push({ role: 'user', content: texto });
        input.value = '';
        suggestions.innerHTML = '';

        var carregando = addMsg('…', 'bot');
        fetch(CHAT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ message: texto, history: history }),
        })
            .then(function (r) {
                if (!r.ok) throw new Error('chat ' + r.status);
                return r.json();
            })
            .then(function (data) {
                carregando.innerHTML = render(data.reply || data.error || 'Não entendi. Pode repetir?');
                if (data.reply) history.push({ role: 'assistant', content: data.reply });
                messages.scrollTop = messages.scrollHeight;
            })
            .catch(function () {
                carregando.innerHTML = 'Ops, tive um problema. Tente de novo.';
            });
    }

    function abrir() {
        panel.hidden = false;
        fab.classList.add('ativo');
        init();
        setTimeout(function () { input.focus(); }, 100);
    }
    function fechar() {
        panel.hidden = true;
        fab.classList.remove('ativo');
    }

    fab.addEventListener('click', function () {
        if (panel.hidden) { abrir(); } else { fechar(); }
    });
    if (closeBtn) closeBtn.addEventListener('click', fechar);

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        enviar(input.value);
    });
})();

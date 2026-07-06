(function () {
    'use strict';

    const cart = {};
    const listEl = document.getElementById('pdv-cart-list');
    const emptyEl = document.getElementById('pdv-cart-empty');
    const totalEl = document.getElementById('pdv-total');
    const form = document.getElementById('pdv-form');
    const submitBtn = document.getElementById('pdv-submit');

    if (!listEl || !form) return;

    function formatBRL(n) {
        return 'R$ ' + n.toFixed(2).replace('.', ',');
    }

    function render() {
        listEl.innerHTML = '';
        let total = 0;
        const keys = Object.keys(cart);
        emptyEl.style.display = keys.length ? 'none' : 'block';
        submitBtn.disabled = !keys.length;

        keys.forEach(function (id) {
            const item = cart[id];
            total += item.preco * item.qtd;

            const li = document.createElement('li');
            li.className = 'pdv-cart-item';
            li.innerHTML =
                '<span>' + item.nome + '</span>' +
                '<div class="pdv-cart-qty">' +
                '<button type="button" data-act="minus" data-id="' + id + '">−</button>' +
                '<span>' + item.qtd + '</span>' +
                '<button type="button" data-act="plus" data-id="' + id + '">+</button>' +
                '</div>' +
                '<strong>' + formatBRL(item.preco * item.qtd) + '</strong>';

            const hidId = document.createElement('input');
            hidId.type = 'hidden';
            hidId.name = 'produto_id';
            hidId.value = id;
            const hidQtd = document.createElement('input');
            hidQtd.type = 'hidden';
            hidQtd.name = 'quantidade';
            hidQtd.value = item.qtd;
            li.appendChild(hidId);
            li.appendChild(hidQtd);
            listEl.appendChild(li);
        });

        totalEl.textContent = formatBRL(total);
    }

    document.querySelectorAll('.pdv-produto-card').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const id = btn.dataset.id;
            const estoque = parseInt(btn.dataset.estoque, 10);
            if (!cart[id]) {
                cart[id] = {
                    nome: btn.dataset.nome,
                    preco: parseFloat(btn.dataset.preco) || 0,
                    qtd: 0,
                    estoque: estoque,
                };
            }
            if (cart[id].qtd >= cart[id].estoque) return;
            cart[id].qtd += 1;
            render();
        });
    });

    listEl.addEventListener('click', function (e) {
        const btn = e.target.closest('button[data-act]');
        if (!btn) return;
        const id = btn.dataset.id;
        const act = btn.dataset.act;
        if (!cart[id]) return;
        if (act === 'plus' && cart[id].qtd < cart[id].estoque) cart[id].qtd += 1;
        if (act === 'minus') {
            cart[id].qtd -= 1;
            if (cart[id].qtd <= 0) delete cart[id];
        }
        render();
    });
})();

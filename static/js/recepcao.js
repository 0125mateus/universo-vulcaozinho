(function () {
    'use strict';

    const FAIXAS = [
        { max: 2, label: 'Bebê (0-2 anos)' },
        { max: 11, label: 'Infantil (3-11 anos)' },
        { max: 17, label: 'Adolescente (12-17 anos)' },
        { max: 59, label: 'Adulto (18-59 anos)' },
        { max: 999, label: 'Terceira idade (60+ anos)' },
    ];

    function calcularIdade(dataStr) {
        const nasc = new Date(dataStr + 'T12:00:00');
        if (Number.isNaN(nasc.getTime())) return null;
        const hoje = new Date();
        let idade = hoje.getFullYear() - nasc.getFullYear();
        const m = hoje.getMonth() - nasc.getMonth();
        if (m < 0 || (m === 0 && hoje.getDate() < nasc.getDate())) idade -= 1;
        return idade;
    }

    function faixaPorIdade(idade) {
        if (idade === null || idade < 0) return null;
        for (const faixa of FAIXAS) {
            if (idade <= faixa.max) return faixa.label;
        }
        return FAIXAS[FAIXAS.length - 1].label;
    }

    const nascInput = document.getElementById('id_data_nascimento');
    const preview = document.getElementById('faixa-preview');
    const labelEl = document.getElementById('faixa-label');

    function atualizarFaixa() {
        if (!nascInput || !preview || !labelEl) return;
        const val = nascInput.value;
        if (!val) {
            preview.hidden = true;
            return;
        }
        const idade = calcularIdade(val);
        const label = faixaPorIdade(idade);
        if (label) {
            labelEl.textContent = label + (idade !== null ? ' (' + idade + ' anos)' : '');
            preview.hidden = false;
        } else {
            preview.hidden = true;
        }
    }

    if (nascInput) {
        nascInput.addEventListener('change', atualizarFaixa);
        nascInput.addEventListener('input', atualizarFaixa);
        atualizarFaixa();
    }

    const modal = document.getElementById('presenca-modal');
    const modalBody = document.getElementById('presenca-modal-body');
    const modalTitle = document.getElementById('presenca-modal-title');
    const modalClose = document.getElementById('presenca-modal-close');

    document.querySelectorAll('.btn-presenca').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (!modal || !modalBody) return;
            const url = btn.dataset.url;
            const titulo = btn.dataset.titulo || 'Registrar presença';
            if (modalTitle) modalTitle.textContent = titulo;
            modalBody.innerHTML = 'Carregando…';
            modal.showModal();
            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.text(); })
                .then(function (html) { modalBody.innerHTML = html; })
                .catch(function () { modalBody.innerHTML = '<p class="rec-empty">Erro ao carregar.</p>'; });
        });
    });

    if (modalClose && modal) {
        modalClose.addEventListener('click', function () { modal.close(); });
    }
})();

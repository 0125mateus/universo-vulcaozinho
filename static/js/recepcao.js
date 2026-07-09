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

    const responsavelSection = document.getElementById('responsavel-section');
    const assinaturaInput = document.getElementById('id_responsavel_assinatura');

    const signaturePad = initSignaturePad();

    function atualizarResponsavel() {
        if (!responsavelSection || !nascInput) return;
        const val = nascInput.value;
        const idade = val ? calcularIdade(val) : null;
        const menor = idade !== null && idade >= 0 && idade < 18;
        const estavaOculto = responsavelSection.hidden;
        responsavelSection.hidden = !menor;
        if (menor && estavaOculto && signaturePad) {
            requestAnimationFrame(function () { signaturePad.ajustar(); });
        }
    }

    function atualizarTudo() {
        atualizarFaixa();
        atualizarResponsavel();
    }

    if (nascInput) {
        nascInput.addEventListener('change', atualizarTudo);
        nascInput.addEventListener('input', atualizarTudo);
        atualizarTudo();
    }

    if (window.VulcaozinhoDocMask) {
        window.VulcaozinhoDocMask.initAll();
    }

    function initSignaturePad() {
        const canvas = document.getElementById('signature-pad');
        const clearBtn = document.getElementById('signature-clear');
        if (!canvas || !assinaturaInput) return null;

        const ctx = canvas.getContext('2d');
        let desenhando = false;
        let temTraco = false;
        let larguraCss = 0;

        function estilizar() {
            ctx.lineWidth = 2.2;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = '#1a1a1a';
        }

        function ajustar() {
            const rect = canvas.getBoundingClientRect();
            if (!rect.width) return;
            const ratio = window.devicePixelRatio || 1;
            const dadosAntigos = temTraco ? assinaturaInput.value : '';
            larguraCss = rect.width;
            canvas.width = rect.width * ratio;
            canvas.height = 200 * ratio;
            canvas.style.height = '200px';
            ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
            estilizar();
            if (dadosAntigos) {
                const img = new Image();
                img.onload = function () { ctx.drawImage(img, 0, 0, rect.width, 200); };
                img.src = dadosAntigos;
            }
        }

        function posicao(evt) {
            const rect = canvas.getBoundingClientRect();
            const src = evt.touches && evt.touches.length ? evt.touches[0] : evt;
            return { x: src.clientX - rect.left, y: src.clientY - rect.top };
        }

        function iniciar(evt) {
            evt.preventDefault();
            if (!larguraCss) ajustar();
            desenhando = true;
            const p = posicao(evt);
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
        }

        function mover(evt) {
            if (!desenhando) return;
            evt.preventDefault();
            const p = posicao(evt);
            ctx.lineTo(p.x, p.y);
            ctx.stroke();
            temTraco = true;
        }

        function terminar() {
            if (!desenhando) return;
            desenhando = false;
            if (temTraco) {
                assinaturaInput.value = canvas.toDataURL('image/png');
            }
        }

        canvas.addEventListener('mousedown', iniciar);
        canvas.addEventListener('mousemove', mover);
        window.addEventListener('mouseup', terminar);
        canvas.addEventListener('touchstart', iniciar, { passive: false });
        canvas.addEventListener('touchmove', mover, { passive: false });
        canvas.addEventListener('touchend', terminar);

        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                assinaturaInput.value = '';
                temTraco = false;
            });
        }

        window.addEventListener('resize', function () {
            if (canvas.getBoundingClientRect().width) ajustar();
        });

        return { ajustar: ajustar };
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

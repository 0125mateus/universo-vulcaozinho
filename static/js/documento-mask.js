(function () {
    'use strict';

    function soDigitos(val) {
        return (val || '').replace(/\D/g, '');
    }

    function mascaraCPF(digits) {
        digits = digits.slice(0, 11);
        if (digits.length <= 3) return digits;
        if (digits.length <= 6) return digits.slice(0, 3) + '.' + digits.slice(3);
        if (digits.length <= 9) {
            return digits.slice(0, 3) + '.' + digits.slice(3, 6) + '.' + digits.slice(6);
        }
        return (
            digits.slice(0, 3) + '.' + digits.slice(3, 6) + '.' +
            digits.slice(6, 9) + '-' + digits.slice(9)
        );
    }

    function mascaraCNPJ(digits) {
        digits = digits.slice(0, 14);
        if (digits.length <= 2) return digits;
        if (digits.length <= 5) return digits.slice(0, 2) + '.' + digits.slice(2);
        if (digits.length <= 8) {
            return digits.slice(0, 2) + '.' + digits.slice(2, 5) + '.' + digits.slice(5);
        }
        if (digits.length <= 12) {
            return (
                digits.slice(0, 2) + '.' + digits.slice(2, 5) + '.' +
                digits.slice(5, 8) + '/' + digits.slice(8)
            );
        }
        return (
            digits.slice(0, 2) + '.' + digits.slice(2, 5) + '.' +
            digits.slice(5, 8) + '/' + digits.slice(8, 12) + '-' + digits.slice(12)
        );
    }

    function mascaraRG(digits) {
        digits = digits.slice(0, 9);
        if (digits.length <= 2) return digits;
        if (digits.length <= 5) return digits.slice(0, 2) + '.' + digits.slice(2);
        if (digits.length <= 8) {
            return digits.slice(0, 2) + '.' + digits.slice(2, 5) + '.' + digits.slice(5);
        }
        return digits.slice(0, 2) + '.' + digits.slice(2, 5) + '.' + digits.slice(5, 8) + '-' + digits.slice(8);
    }

    function formatarDocumento(val) {
        const raw = (val || '').trim();
        if (!raw) return '';

        if (/[a-zA-Z]/.test(raw)) {
            return raw.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
        }

        const digits = soDigitos(raw);
        if (!digits) return '';

        if (digits.length <= 11) return mascaraCPF(digits);
        if (digits.length <= 14) return mascaraCNPJ(digits);
        return mascaraRG(digits);
    }

    function posicaoAposDigitos(texto, qtdDigitos) {
        if (qtdDigitos <= 0) return 0;
        let count = 0;
        for (let i = 0; i < texto.length; i++) {
            if (/\d/.test(texto[i])) count++;
            if (count >= qtdDigitos) return i + 1;
        }
        return texto.length;
    }

    function aplicarMascara(input) {
        const valorAtual = input.value;
        const cursor = input.selectionStart ?? valorAtual.length;
        const digitosAntesCursor = soDigitos(valorAtual.slice(0, cursor)).length;
        const formatado = formatarDocumento(valorAtual);

        input.value = formatado;

        const novaPos = posicaoAposDigitos(formatado, digitosAntesCursor);
        try {
            input.setSelectionRange(novaPos, novaPos);
        } catch (e) {
            /* input pode estar sem foco */
        }
    }

    function initDocumentoInput(input) {
        if (!input || input.dataset.docMaskInit === '1') return;
        input.dataset.docMaskInit = '1';
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('spellcheck', 'false');

        input.addEventListener('input', function () {
            aplicarMascara(input);
        });
        input.addEventListener('paste', function () {
            setTimeout(function () { aplicarMascara(input); }, 0);
        });
        input.addEventListener('blur', function () {
            input.value = formatarDocumento(input.value);
        });

        if (input.value) {
            input.value = formatarDocumento(input.value);
        }
    }

    function initTodos() {
        document.querySelectorAll('.doc-input, #id_documento').forEach(initDocumentoInput);
    }

    window.VulcaozinhoDocMask = {
        formatar: formatarDocumento,
        init: initDocumentoInput,
        initAll: initTodos,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTodos);
    } else {
        initTodos();
    }
})();

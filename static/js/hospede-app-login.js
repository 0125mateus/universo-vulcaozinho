(function () {
    'use strict';

    var aptInput = document.querySelector('#app-login-form input[name="apartamento"]');
    var docInput = document.querySelector('#app-login-form input[name="documento"]');
    var detectBox = document.getElementById('app-hotel-detect');
    var detectNome = document.getElementById('app-hotel-detect-nome');
    var defaultLabel = document.getElementById('app-hotel-default');
    var logoEl = document.getElementById('app-hotel-logo');
    var defaultLogo = logoEl ? (logoEl.dataset.defaultSrc || logoEl.src) : '';
    var timer = null;

    if (!aptInput || !docInput || !detectBox) {
        return;
    }

    function soDigitos(val) {
        return (val || '').replace(/\D/g, '');
    }

    function limparDeteccao() {
        detectBox.hidden = true;
        if (defaultLabel) {
            defaultLabel.hidden = false;
        }
        if (logoEl && defaultLogo) {
            logoEl.src = defaultLogo;
            logoEl.classList.remove('is-hotel-logo');
        }
        document.documentElement.style.removeProperty('--app-primary');
    }

    function mostrarHotel(data) {
        detectNome.textContent = data.hotel_nome;
        detectBox.hidden = false;
        if (defaultLabel) {
            defaultLabel.hidden = true;
        }
        if (logoEl && data.hotel_slug) {
            logoEl.src = '/static/img/hoteis/' + data.hotel_slug + '.png';
            logoEl.classList.add('is-hotel-logo');
        }
        if (data.hotel_cor) {
            document.documentElement.style.setProperty('--app-primary', data.hotel_cor);
        }
        if (data.primeiro_nome) {
            var titulo = document.querySelector('.app-login-hero h1');
            if (titulo) {
                titulo.textContent = 'Olá, ' + data.primeiro_nome + '!';
            }
        }
    }

    function identificarHotel() {
        var apt = (aptInput.value || '').trim();
        var doc = soDigitos(docInput.value);
        if (!apt || doc.length < 4) {
            limparDeteccao();
            return;
        }

        var params = new URLSearchParams({
            apartamento: apt,
            documento: docInput.value.trim(),
        });

        fetch('/app/identificar-hotel/?' + params.toString(), {
            headers: { Accept: 'application/json' },
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.ok) {
                    mostrarHotel(data);
                } else {
                    limparDeteccao();
                }
            })
            .catch(function () {
                limparDeteccao();
            });
    }

    function agendarIdentificacao() {
        clearTimeout(timer);
        timer = setTimeout(identificarHotel, 350);
    }

    aptInput.addEventListener('input', agendarIdentificacao);
    docInput.addEventListener('input', agendarIdentificacao);
    aptInput.addEventListener('blur', identificarHotel);
    docInput.addEventListener('blur', identificarHotel);
})();

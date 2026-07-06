(function () {
    'use strict';

    const POLL_MS = 15000;
    const FALLBACK_ONLY_MS = 120000;
    const WEATHER_MS = 30 * 60 * 1000;
    const POCOS_LAT = -21.7877;
    const POCOS_LON = -46.5614;

    const WMO = {
        0: { icon: '☀️', label: 'Ensolarado' },
        1: { icon: '🌤️', label: 'Principalmente limpo' },
        2: { icon: '⛅', label: 'Parcialmente nublado' },
        3: { icon: '☁️', label: 'Nublado' },
        45: { icon: '🌫️', label: 'Neblina' },
        48: { icon: '🌫️', label: 'Neblina gelada' },
        51: { icon: '🌦️', label: 'Garoa leve' },
        53: { icon: '🌦️', label: 'Garoa' },
        55: { icon: '🌧️', label: 'Garoa forte' },
        61: { icon: '🌧️', label: 'Chuva fraca' },
        63: { icon: '🌧️', label: 'Chuva' },
        65: { icon: '🌧️', label: 'Chuva forte' },
        71: { icon: '🌨️', label: 'Neve' },
        80: { icon: '🌦️', label: 'Pancadas de chuva' },
        95: { icon: '⛈️', label: 'Tempestade' },
    };

    const app = document.getElementById('telao-app');
    if (!app) return;

    const HOTEL_ID = app.dataset.hotelId;
    const API_KEY = app.dataset.apiKey;
    const API_BASE = app.dataset.apiBase || '/api/v1/';
    const TV_MODE = app.dataset.tvMode === '1';

    function $(id) { return document.getElementById(id); }

    function updateClock() {
        const el = $('telao-clock');
        if (el) {
            el.textContent = new Date().toLocaleTimeString('pt-BR', {
                hour: '2-digit',
                minute: '2-digit',
            });
        }
    }

    function calcIdade(dataNascimento) {
        if (!dataNascimento) return null;
        const nasc = new Date(dataNascimento + 'T12:00:00');
        const hoje = new Date();
        let idade = hoje.getFullYear() - nasc.getFullYear();
        const m = hoje.getMonth() - nasc.getMonth();
        if (m < 0 || (m === 0 && hoje.getDate() < nasc.getDate())) idade -= 1;
        return idade;
    }

    function formatHora(timeStr) {
        if (!timeStr) return '—';
        const parts = timeStr.slice(0, 5).split(':');
        return parseInt(parts[0], 10) + 'h' + parts[1];
    }

    function primeiroNome(nome) {
        return (nome || '').split(' ')[0] || nome;
    }

    async function fetchTelao(path) {
        const url = API_BASE + path + (path.includes('?') ? '&' : '?') + 'api_key=' + encodeURIComponent(API_KEY);
        const res = await fetch(url);
        if (!res.ok) throw new Error(res.status);
        return res.json();
    }

    function renderClima(code, temp) {
        const info = WMO[code] || { icon: '🌡️', label: 'Clima variável' };
        const tempEl = $('telao-temp');
        const climaEl = $('telao-clima');
        const iconEl = $('telao-weather-icon');
        const climaIcon = $('telao-clima-icon');

        if (tempEl && temp != null) {
            tempEl.textContent = Math.round(temp) + '°C';
        }
        if (iconEl) iconEl.textContent = info.icon;
        if (climaIcon) climaIcon.textContent = info.icon;
        if (climaEl) climaEl.textContent = info.label;
    }

    async function refreshWeather() {
        try {
            const url = 'https://api.open-meteo.com/v1/forecast?latitude='
                + POCOS_LAT + '&longitude=' + POCOS_LON
                + '&current=temperature_2m,weather_code&timezone=America/Sao_Paulo';
            const res = await fetch(url);
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            const cur = data.current || {};
            renderClima(cur.weather_code, cur.temperature_2m);
        } catch (e) {
            console.warn('Clima:', e);
            renderClima(2, 22);
        }
    }

    function renderAtividade(prog, emAndamento) {
        const label = $('telao-hero-label');
        const nome = $('telao-atividade-nome');
        const hora = $('telao-atividade-hora');
        const local = $('telao-atividade-local');

        const exibir = prog || emAndamento;
        if (!exibir) {
            if (label) label.textContent = 'RECREAÇÃO';
            if (nome) nome.textContent = 'EM BREVE MAIS DIVERSÃO!';
            if (hora) hora.textContent = '🌋';
            if (local) local.textContent = 'Fique atento à programação';
            return;
        }

        if (label) label.textContent = prog ? 'PRÓXIMA ATIVIDADE' : 'AGORA';
        if (nome) nome.textContent = (exibir.atividade_nome || 'ATIVIDADE').toUpperCase();
        if (hora) hora.textContent = formatHora(exibir.hora_inicio);
        if (local) {
            const loc = exibir.local_nome || '';
            const fim = exibir.hora_fim ? formatHora(exibir.hora_fim) : '';
            local.textContent = loc ? (loc + (fim ? ' · até ' + fim : '')) : '';
        }
    }

    function renderAniversariantes(lista) {
        const ul = $('telao-nivers');
        if (!ul) return;
        const items = lista || [];
        if (!items.length) {
            ul.innerHTML = '<li class="telao-nivers-empty">Nenhum aniversariante hoje</li>';
            return;
        }
        ul.innerHTML = items.map(function (h) {
            const idade = calcIdade(h.data_nascimento);
            const nome = primeiroNome(h.nome_completo);
            const idadeTxt = idade !== null ? ' ' + idade + ' anos' : '';
            return '<li><span>' + nome + idadeTxt + '</span></li>';
        }).join('');
    }

    function renderPasseios(passeios) {
        const el = $('telao-passeio');
        if (!el) return;
        const lista = passeios || [];
        if (!lista.length) {
            el.textContent = 'Consulte a recepção';
            return;
        }
        el.textContent = lista[0].titulo;
    }

    async function refresh() {
        try {
            const [prog, nivers, passeiosData] = await Promise.all([
                fetchTelao('telao/' + HOTEL_ID + '/programacao-atual/'),
                fetchTelao('telao/' + HOTEL_ID + '/aniversariantes-hoje/'),
                fetchTelao('telao/' + HOTEL_ID + '/passeios-hoje/'),
            ]);
            renderAtividade(prog.proxima, prog.em_andamento);
            renderAniversariantes(nivers.aniversariantes);
            renderPasseios(passeiosData.passeios);

            const upd = $('telao-updated');
            if (upd) upd.textContent = 'Atualizado ' + new Date().toLocaleTimeString('pt-BR');
        } catch (e) {
            console.error('Telão:', e);
            const nome = $('telao-atividade-nome');
            if (nome) nome.textContent = 'ERRO AO CARREGAR';
        }
    }

    function enterFullscreen() {
        const target = TV_MODE ? document.documentElement : document.querySelector('.telao-bezel');
        if (target && target.requestFullscreen) {
            target.requestFullscreen().catch(function () {});
        }
    }

    let telaoWsLive = false;

    function connectTelaoWs() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = proto + '//' + location.host + '/ws/telao/' + HOTEL_ID
            + '/?api_key=' + encodeURIComponent(API_KEY);
        const ws = new WebSocket(url);

        ws.onopen = function () { telaoWsLive = true; };

        ws.onmessage = function (ev) {
            try {
                const data = JSON.parse(ev.data);
                if (data.event === 'refresh' || data.event === 'connected') {
                    refresh();
                }
            } catch (e) {
                refresh();
            }
        };

        ws.onclose = function () {
            telaoWsLive = false;
            setTimeout(connectTelaoWs, 3000);
        };

        ws.onerror = function () { ws.close(); };
    }

    updateClock();
    setInterval(updateClock, 1000);
    refresh();
    refreshWeather();
    setInterval(refreshWeather, WEATHER_MS);
    setInterval(function () {
        if (!telaoWsLive) refresh();
    }, POLL_MS);
    setInterval(refresh, FALLBACK_ONLY_MS);
    connectTelaoWs();
    enterFullscreen();
})();

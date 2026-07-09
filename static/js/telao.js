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

    function formatData(iso) {
        if (!iso) return '';
        const d = new Date(iso + 'T12:00:00');
        const hoje = new Date();
        hoje.setHours(12, 0, 0, 0);
        if (d.toDateString() === hoje.toDateString()) return 'Hoje';
        const amanha = new Date(hoje);
        amanha.setDate(amanha.getDate() + 1);
        if (d.toDateString() === amanha.toDateString()) return 'Amanhã';
        return d.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'short' });
    }

    function escHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatHoraCurta(timeStr) {
        if (!timeStr) return '—';
        const parts = timeStr.slice(0, 5).split(':');
        return parts[0].padStart(2, '0') + ':' + parts[1];
    }

    function formatHoraIntervalo(inicio, fim) {
        if (!inicio) return '—';
        const ini = formatHoraCurta(inicio);
        return fim ? ini + ' – ' + formatHoraCurta(fim) : ini;
    }

    function atividadeEmAndamento(item) {
        if (!item || !item.hora_inicio || !item.hora_fim) return false;
        const now = new Date();
        const cur = now.getHours() * 60 + now.getMinutes();
        const partsIni = item.hora_inicio.split(':');
        const partsFim = item.hora_fim.split(':');
        const ini = parseInt(partsIni[0], 10) * 60 + parseInt(partsIni[1], 10);
        const fim = parseInt(partsFim[0], 10) * 60 + parseInt(partsFim[1], 10);
        return cur >= ini && cur < fim;
    }

    function esconderGradeBoard() {
        const board = $('telao-grade-board');
        const single = $('telao-hero-single');
        const hero = $('telao-hero');
        const screen = document.querySelector('.telao-screen');
        if (board) board.hidden = true;
        if (single) single.hidden = false;
        if (hero) hero.classList.remove('telao-modo-grade');
        if (screen) screen.classList.remove('telao-screen-grade');
    }

    function mostrarGradeBoard() {
        const board = $('telao-grade-board');
        const single = $('telao-hero-single');
        const hero = $('telao-hero');
        const screen = document.querySelector('.telao-screen');
        if (board) board.hidden = false;
        if (single) single.hidden = true;
        if (hero) hero.classList.add('telao-modo-grade');
        if (screen) screen.classList.add('telao-screen-grade');
    }

    function renderGradeColunas(gradeData) {
        const board = $('telao-grade-board');
        const colunasEl = $('telao-grade-colunas');
        const dataEl = $('telao-grade-data');
        if (!board || !colunasEl) return;

        const colunas = (gradeData && gradeData.colunas) || [];
        if (!colunas.length) {
            esconderGradeBoard();
            return;
        }

        mostrarGradeBoard();

        if (dataEl && gradeData.data) {
            dataEl.textContent = formatData(gradeData.data) + ' · ' + (gradeData.total || 0) + ' atividades';
        }

        const nCols = colunas.length;
        colunasEl.style.gridTemplateColumns = 'repeat(' + nCols + ', minmax(0, 1fr))';

        colunasEl.innerHTML = colunas.map(function (col) {
            const idade = (col.idade_min != null && col.idade_max != null)
                ? col.idade_min + '–' + col.idade_max + ' anos'
                : '';
            const tituloFaixa = escHtml(col.faixa_icone) + ' ' + escHtml(col.faixa) +
                (idade ? ' (' + idade + ')' : '');
            const atividades = col.atividades || [];
            const lista = atividades.length
                ? atividades.map(function (a) {
                    const agora = atividadeEmAndamento(a);
                    const metaParts = [];
                    if (a.local) metaParts.push(a.local);
                    if (a.recreador) metaParts.push(a.recreador);
                    const meta = metaParts.join(' · ');
                    return '<li class="telao-grade-atividade' + (agora ? ' telao-grade-atividade-now' : '') + '">' +
                        '<div class="telao-grade-hora">' + formatHoraIntervalo(a.hora_inicio, a.hora_fim) + '</div>' +
                        '<div class="telao-grade-nome">' + escHtml(a.icone || '⭐') + ' ' + escHtml(a.nome) + '</div>' +
                        (meta ? '<div class="telao-grade-meta">' + escHtml(meta) + '</div>' : '') +
                        '</li>';
                }).join('')
                : '<li class="telao-grade-vazio">Nenhuma atividade hoje.</li>';

            return '<article class="telao-grade-coluna" style="--faixa-cor:' + escHtml(col.faixa_cor || '#1E6B43') + '">' +
                '<header class="telao-grade-col-head">' + tituloFaixa + '</header>' +
                '<ul class="telao-grade-lista">' + lista + '</ul>' +
                '</article>';
        }).join('');
    }

    function aplicarModoExibicao(prog, gradeData) {
        const publicada = gradeData && gradeData.publicada;
        const colunas = (gradeData && gradeData.colunas) || [];
        if (publicada && colunas.length) {
            renderGradeColunas(gradeData);
            return;
        }
        esconderGradeBoard();
        renderAtividade(prog);
    }

    function renderAtividade(data) {
        const label = $('telao-hero-label');
        const nome = $('telao-atividade-nome');
        const hora = $('telao-atividade-hora');
        const local = $('telao-atividade-local');

        const status = (data && data.status) || 'vazio';
        const exibir = (data && (data.destaque || data.em_andamento || data.proxima)) || null;

        if (!exibir) {
            if (label) label.textContent = 'RECREAÇÃO';
            if (nome) nome.textContent = 'EM BREVE MAIS DIVERSÃO!';
            if (hora) hora.textContent = '🌋';
            if (local) {
                const total = data && data.total_hoje ? data.total_hoje : 0;
                local.textContent = total
                    ? 'Sem atividades no horário — veja a programação completa'
                    : 'Fique atento à programação';
            }
            return;
        }

        const rotulos = {
            em_andamento: 'AGORA',
            proxima: 'PRÓXIMA ATIVIDADE',
            amanha: 'AMANHÃ',
            encerrado: 'PROGRAMAÇÃO DE HOJE',
        };

        if (label) label.textContent = rotulos[status] || 'RECREAÇÃO';

        if (status === 'encerrado') {
            if (nome) nome.textContent = 'ENCERRADA POR HOJE';
            if (hora) hora.textContent = formatHora(exibir.hora_fim || exibir.hora_inicio);
            if (local) {
                local.textContent = 'Última: ' + (exibir.atividade_nome || '—') +
                    (data.total_hoje ? ' · ' + data.total_hoje + ' atividades hoje' : '');
            }
            return;
        }

        if (nome) nome.textContent = (exibir.atividade_nome || 'ATIVIDADE').toUpperCase();
        if (hora) {
            const prefixo = status === 'amanha' ? formatData(exibir.data) + ' · ' : '';
            hora.textContent = prefixo + formatHora(exibir.hora_inicio);
        }
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
            const [prog, nivers, passeiosData, gradeData] = await Promise.all([
                fetchTelao('telao/' + HOTEL_ID + '/programacao-atual/'),
                fetchTelao('telao/' + HOTEL_ID + '/aniversariantes-hoje/'),
                fetchTelao('telao/' + HOTEL_ID + '/passeios-hoje/'),
                fetchTelao('telao/' + HOTEL_ID + '/grade-publicada/'),
            ]);
            aplicarModoExibicao(prog, gradeData);
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
                if (data.event === 'refresh' || data.event === 'connected'
                    || data.event === 'grade_publicada' || data.event === 'grade_removida') {
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

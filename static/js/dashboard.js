/**
 * Dashboard operacional — tempo real via WebSocket + fallback polling.
 */
(function () {
    'use strict';

    const FALLBACK_POLL_MS = 120000;
    const root = document.getElementById('dashboard-root');
    if (!root) return;

    const API_BASE = root.dataset.apiBase || '/api/v1/';
    const HOJE = root.dataset.hoje;
    const DIA_SEMANA = root.dataset.diaSemana;

    let chartFaixas = null;
    let wsLive = false;

    function $(id) { return document.getElementById(id); }

    function cssVar(name, fallback) {
        const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return val || fallback;
    }

    function getHotelPalette() {
        return [
            cssVar('--hotel-accent', '#FFED00'),
            cssVar('--hotel-secondary', '#8DC63F'),
            cssVar('--hotel-tertiary', '#F7941D'),
            cssVar('--hotel-primary', '#006838'),
            cssVar('--brand-blue', '#00B5E2'),
            cssVar('--brand-pink', '#ED1E79'),
        ];
    }

    async function apiGet(path) {
        const res = await fetch(API_BASE + path, {
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        });
        if (res.status === 403 || res.status === 401) {
            window.location.href = '/entrar/?next=/dashboard/';
            return null;
        }
        if (!res.ok) throw new Error('API ' + res.status);
        return res.json();
    }

    async function fetchAllPages(path) {
        const items = [];
        let url = path;
        while (url) {
            const data = await apiGet(url.replace(API_BASE, ''));
            if (!data) return items;
            items.push(...(data.results || []));
            if (data.next) {
                url = data.next.startsWith('http') ? new URL(data.next).pathname + new URL(data.next).search : data.next;
                url = url.replace(/^\/api\/v1\//, '');
            } else {
                url = null;
            }
        }
        return items;
    }

    function agruparFaixas(hospedes) {
        const map = {};
        hospedes.forEach(function (h) {
            const label = h.faixa_etaria_label || h.faixa_etaria || 'Outros';
            map[label] = (map[label] || 0) + 1;
        });
        return map;
    }

    function aniversariantesHoje(hospedes) {
        if (!HOJE) return [];
        const parts = HOJE.split('-');
        const mm = parts[1];
        const dd = parts[2];
        return hospedes.filter(function (h) {
            if (!h.data_nascimento) return false;
            const p = h.data_nascimento.split('-');
            return p[1] === mm && p[2] === dd;
        });
    }

    function programacaoAtual(progs) {
        const now = new Date();
        const nowMin = now.getHours() * 60 + now.getMinutes();

        function toMin(t) {
            if (!t) return -1;
            const p = t.split(':');
            return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
        }

        let emAndamento = null;
        let proxima = null;

        progs.forEach(function (p) {
            const ini = toMin(p.hora_inicio);
            const fim = toMin(p.hora_fim);
            if (ini <= nowMin && fim > nowMin) emAndamento = p;
            if (ini > nowMin && (!proxima || ini < toMin(proxima.hora_inicio))) proxima = p;
        });

        return { emAndamento, proxima };
    }

    function renderChart(faixasMap) {
        const labels = Object.keys(faixasMap);
        const values = labels.map(function (k) { return faixasMap[k]; });
        const ctx = $('chart-faixas');
        if (!ctx) return;

        const palette = getHotelPalette();

        if (chartFaixas) chartFaixas.destroy();

        chartFaixas = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(function (_, i) {
                        return palette[i % palette.length];
                    }),
                    borderColor: '#fff',
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { weight: '700' } },
                    },
                },
            },
        });
    }

    function setOcupacao(prog) {
        const el = $('metric-ocupacao');
        const bar = $('bar-ocupacao');
        if (!prog) {
            if (el) el.textContent = 'Nenhuma atividade agora';
            if (bar) bar.style.width = '0%';
            return;
        }
        const presentes = prog.presentes_count || 0;
        const total = prog.vagas_total || 1;
        const pct = Math.min(100, Math.round((presentes / total) * 100));
        if (el) el.textContent = presentes + ' / ' + total + ' presentes (' + pct + '%)';
        if (bar) {
            bar.style.width = pct + '%';
            bar.style.background = 'linear-gradient(90deg, '
                + cssVar('--hotel-primary', '#006838') + ', '
                + cssVar('--hotel-secondary', '#8DC63F') + ')';
            bar.className = 'progress-bar';
        }
    }

    async function refresh() {
        try {
            const [hospedes, programacao, produtos, passaportes, passeios] = await Promise.all([
                fetchAllPages('hospedes/?ativos=1'),
                fetchAllPages('programacao/?data=' + HOJE),
                fetchAllPages('produtos/'),
                fetchAllPages('passaportes/?com_carimbo=1'),
                fetchAllPages('passeios/?dia=' + DIA_SEMANA),
            ]);

            $('metric-hospedes-total').textContent = hospedes.length;

            const nivers = aniversariantesHoje(hospedes);
            $('metric-aniversariantes').textContent = nivers.length;
            const lista = $('lista-aniversariantes');
            if (lista) {
                lista.innerHTML = nivers.slice(0, 5).map(function (h) {
                    return '<li>' + h.nome_completo + ' (apt. ' + h.apartamento + ')</li>';
                }).join('');
                if (nivers.length > 5) lista.innerHTML += '<li>+' + (nivers.length - 5) + ' mais…</li>';
            }

            const faixas = agruparFaixas(hospedes);
            renderChart(faixas);

            const { emAndamento, proxima } = programacaoAtual(programacao);
            $('metric-atual').textContent = emAndamento
                ? (emAndamento.atividade_nome || 'Atividade')
                : 'Nenhuma';
            $('metric-atual-local').textContent = emAndamento
                ? (emAndamento.local_nome || '') + (emAndamento.hora_inicio ? ' · ' + emAndamento.hora_inicio.slice(0, 5) : '')
                : '';

            $('metric-proxima').textContent = proxima
                ? (proxima.atividade_nome || 'Atividade')
                : '—';
            $('metric-proxima-hora').textContent = proxima && proxima.hora_inicio
                ? 'Às ' + proxima.hora_inicio.slice(0, 5)
                : '';

            setOcupacao(emAndamento);

            const elLoja = $('metric-loja-produtos');
            const elLojaBaixo = $('metric-loja-estoque-baixo');
            if (elLoja) elLoja.textContent = produtos.length;
            const baixo = produtos.filter(function (p) { return (p.estoque || 0) <= 5; }).length;
            if (elLojaBaixo) elLojaBaixo.textContent = baixo ? baixo + ' com estoque baixo (≤5)' : 'Estoque OK';

            const elPass = $('metric-passaportes');
            if (elPass) {
                elPass.textContent = passaportes.length;
            }

            const elPasseios = $('metric-passeios');
            const elPasseiosDet = $('metric-passeios-detalhe');
            if (elPasseios) elPasseios.textContent = passeios.length;
            if (elPasseiosDet) {
                elPasseiosDet.textContent = passeios.length
                    ? passeios.map(function (p) { return p.titulo; }).join(' · ')
                    : 'Nenhum passeio cadastrado hoje';
            }

            const upd = $('dash-updated');
            if (upd) {
                const modo = wsLive ? 'ao vivo' : 'polling';
                upd.textContent = 'Atualizado às ' + new Date().toLocaleTimeString('pt-BR') + ' (' + modo + ')';
            }
        } catch (err) {
            console.error('Dashboard:', err);
            const upd = $('dash-updated');
            if (upd) upd.textContent = 'Erro ao carregar dados. Tentando de novo…';
        }
    }

    function setLiveBadge(online) {
        const badge = $('dash-live');
        if (!badge) return;
        badge.textContent = online ? '🟢 Ao vivo' : '🟡 Reconectando…';
        badge.className = online ? 'dash-live dash-live-on' : 'dash-live dash-live-off';
    }

    function connectLiveWs() {
        const hotelId = root.dataset.hotelId;
        if (!hotelId) return;

        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(proto + '//' + location.host + '/ws/dashboard/' + hotelId + '/');

        ws.onopen = function () {
            wsLive = true;
            setLiveBadge(true);
        };

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
            wsLive = false;
            setLiveBadge(false);
            setTimeout(connectLiveWs, 3000);
        };

        ws.onerror = function () {
            ws.close();
        };
    }

    connectLiveWs();
    refresh();
    setInterval(function () {
        if (!wsLive) refresh();
    }, FALLBACK_POLL_MS);
})();

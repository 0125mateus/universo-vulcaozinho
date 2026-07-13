(function () {
    const table = document.querySelector('.fin-grid-table');
    if (!table) return;

    const dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'];

    function formatMoney(value) {
        return value.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function parseVal(input) {
        if (!input || input.value === '') return 0;
        const normalized = String(input.value).trim().replace(',', '.');
        const value = parseFloat(normalized);
        return Number.isFinite(value) ? value : 0;
    }

    function rowIsActive(row) {
        if (row.style.display === 'none') return false;
        const del = row.querySelector('input[name$="-DELETE"]');
        return !(del && del.checked);
    }

    function recalc() {
        const totalsDia = Object.fromEntries(dias.map((d) => [d, 0]));
        let totalGeral = 0;

        table.querySelectorAll('tbody tr').forEach((row) => {
            if (!rowIsActive(row)) return;

            let rowTotal = 0;
            dias.forEach((dia) => {
                const input = row.querySelector(`input[name$="-valor_${dia}"]`);
                const value = parseVal(input);
                rowTotal += value;
                totalsDia[dia] += value;
            });

            const rowTotalCell = row.querySelector('.fin-row-total');
            if (rowTotalCell) {
                rowTotalCell.textContent = rowTotal > 0 ? `R$ ${formatMoney(rowTotal)}` : '—';
            }
            totalGeral += rowTotal;
        });

        dias.forEach((dia) => {
            const cell = table.querySelector(`tfoot [data-dia="${dia}"]`);
            if (cell) cell.textContent = `R$ ${formatMoney(totalsDia[dia])}`;
        });

        const footerGeral = table.querySelector('[data-total-geral]');
        if (footerGeral) footerGeral.textContent = `R$ ${formatMoney(totalGeral)}`;

        const headerGeral = document.getElementById('fin-total-geral');
        if (headerGeral) headerGeral.textContent = `R$ ${formatMoney(totalGeral)}`;
    }

    table.addEventListener('input', (event) => {
        if (event.target.matches('.fin-grid-valor, .fin-grid-nome')) {
            recalc();
        }
    });

    table.addEventListener('click', (event) => {
        const trash = event.target.closest('.fin-grid-trash');
        if (!trash) return;

        event.preventDefault();
        const row = trash.closest('tr');
        const del = row.querySelector('input[name$="-DELETE"]');
        if (del) {
            del.checked = true;
            row.style.display = 'none';
        } else {
            row.remove();
        }
        recalc();
    });

    recalc();
})();

(function () {
    'use strict';

    function updateLoteBar() {
        var bar = document.getElementById('prog-lote-bar');
        var countEl = document.getElementById('prog-lote-count');
        var selectAll = document.getElementById('prog-select-all');
        if (!bar || !countEl) return;

        var checks = document.querySelectorAll('.prog-row-check');
        var n = 0;
        checks.forEach(function (c) { if (c.checked) n += 1; });

        countEl.textContent = n + ' selecionada(s)';
        bar.hidden = n === 0;

        if (selectAll && checks.length) {
            selectAll.indeterminate = n > 0 && n < checks.length;
            selectAll.checked = n === checks.length;
        }
    }

    function initLoteList() {
        var selectAll = document.getElementById('prog-select-all');
        if (!selectAll) return;

        selectAll.addEventListener('change', function () {
            document.querySelectorAll('.prog-row-check').forEach(function (c) {
                c.checked = selectAll.checked;
            });
            updateLoteBar();
        });

        document.querySelectorAll('.prog-row-check').forEach(function (c) {
            c.addEventListener('change', updateLoteBar);
        });
    }

    function initBulkForm() {
        var selectAllBtn = document.getElementById('prog-bulk-select-all');
        var clearBtn = document.getElementById('prog-bulk-clear-all');
        if (!selectAllBtn) return;

        var checks = document.querySelectorAll('#form-prog-bulk input[type=checkbox][name=atividades]');

        selectAllBtn.addEventListener('click', function () {
            checks.forEach(function (c) { c.checked = true; });
        });

        clearBtn.addEventListener('click', function () {
            checks.forEach(function (c) { c.checked = false; });
        });
    }

    initLoteList();
    initBulkForm();
})();

(function () {
    const dialog = document.getElementById('galeria-lightbox');
    const img = document.getElementById('galeria-lightbox-img');
    const caption = document.getElementById('galeria-lightbox-caption');
    const closeBtn = document.querySelector('.galeria-lightbox-close');

    function openLightbox(src, cap) {
        if (!dialog || !img) return;
        img.src = src;
        img.alt = cap || '';
        if (caption) caption.textContent = cap || '';
        dialog.showModal();
    }

    document.querySelectorAll('.galeria-item').forEach((btn) => {
        btn.addEventListener('click', () => {
            openLightbox(btn.dataset.src, btn.dataset.caption);
        });
    });

    const zoomBtn = document.getElementById('quadrinho-zoom');
    if (zoomBtn) {
        zoomBtn.addEventListener('click', () => {
            openLightbox(zoomBtn.dataset.src, zoomBtn.dataset.caption);
        });
    }

    if (dialog) {
        function close() {
            dialog.close();
            img.src = '';
        }
        closeBtn?.addEventListener('click', close);
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog || e.target.classList.contains('galeria-lightbox-stage')) close();
        });
        const stage = dialog.querySelector('.galeria-lightbox-stage');
        stage?.addEventListener('click', (e) => {
            if (e.target === stage) close();
        });
        img?.addEventListener('click', (e) => e.stopPropagation());
        dialog.addEventListener('cancel', () => { img.src = ''; });
    }

    /* Leitor de quadrinhos — painel a painel */
    const panels = document.querySelectorAll('.quadrinho-panel');
    const counter = document.getElementById('quad-counter');
    const prevBtn = document.getElementById('quad-prev');
    const nextBtn = document.getElementById('quad-next');
    const gridToggle = document.getElementById('quad-grid-toggle');
    const panelsWrap = document.getElementById('quadrinhos-panels');
    let current = 0;
    let gridMode = false;

    function showPanel(index) {
        if (!panels.length) return;
        current = Math.max(0, Math.min(index, panels.length - 1));
        if (!gridMode) {
            panels.forEach((p, i) => p.classList.toggle('active', i === current));
        }
        if (counter) counter.textContent = `Painel ${current + 1} de ${panels.length}`;
    }

    prevBtn?.addEventListener('click', () => {
        if (gridMode) return;
        showPanel(current - 1 < 0 ? panels.length - 1 : current - 1);
    });
    nextBtn?.addEventListener('click', () => {
        if (gridMode) return;
        showPanel(current + 1 >= panels.length ? 0 : current + 1);
    });

    gridToggle?.addEventListener('click', () => {
        gridMode = !gridMode;
        panelsWrap?.classList.toggle('quadrinhos-grid-mode', gridMode);
        gridToggle.textContent = gridMode ? '▣' : '⊞';
        gridToggle.title = gridMode ? 'Modo leitura' : 'Ver todos';
        if (!gridMode) showPanel(current);
        else panels.forEach((p) => p.classList.add('active'));
    });

    panels.forEach((panel, i) => {
        panel.addEventListener('click', () => {
            if (gridMode) {
                gridMode = false;
                panelsWrap?.classList.remove('quadrinhos-grid-mode');
                if (gridToggle) {
                    gridToggle.textContent = '⊞';
                    gridToggle.title = 'Ver todos';
                }
                showPanel(i);
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (gridMode || dialog?.open) return;
        if (e.key === 'ArrowLeft') prevBtn?.click();
        if (e.key === 'ArrowRight') nextBtn?.click();
    });

    showPanel(0);
})();

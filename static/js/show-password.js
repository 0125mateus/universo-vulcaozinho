/**
 * Adiciona botão "mostrar/ocultar" em todos os inputs type=password.
 */
(function () {
  function enhance(input) {
    if (input.dataset.showPassReady) return;
    input.dataset.showPassReady = '1';

    const wrap = document.createElement('div');
    wrap.className = 'pwd-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pwd-toggle';
    btn.setAttribute('aria-label', 'Mostrar senha');
    btn.textContent = 'Mostrar';
    wrap.appendChild(btn);

    btn.addEventListener('click', () => {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      btn.textContent = showing ? 'Mostrar' : 'Ocultar';
      btn.setAttribute('aria-label', showing ? 'Mostrar senha' : 'Ocultar senha');
    });
  }

  function run() {
    document.querySelectorAll('input[type="password"]').forEach(enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();

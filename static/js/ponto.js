(() => {
  const app = document.getElementById('ponto-app');
  if (!app) return;

  const csrf = app.dataset.csrf;
  const autenticarUrl = app.dataset.autenticarUrl;
  const registrarTpl = app.dataset.registrarUrlTemplate;

  const modal = document.getElementById('ponto-modal');
  const closeBtn = document.getElementById('ponto-modal-close');
  const nomeEl = document.getElementById('ponto-modal-nome');
  const fotoEl = document.getElementById('ponto-modal-foto');
  const fotoEmpty = document.getElementById('ponto-modal-foto-empty');
  const stepAcao = document.getElementById('ponto-step-acao');
  const stepOk = document.getElementById('ponto-step-ok');
  const pinDisplay = document.getElementById('ponto-pin-display');
  const pinErro = document.getElementById('ponto-pin-erro');
  const acaoErro = document.getElementById('ponto-acao-erro');
  const acaoSugerida = document.getElementById('ponto-acao-sugerida');
  const extraToggle = document.getElementById('ponto-extra');
  const sucessoMsg = document.getElementById('ponto-sucesso-msg');
  const video = document.getElementById('ponto-video');
  const canvas = document.getElementById('ponto-canvas');
  const preview = document.getElementById('ponto-preview');
  const fotoBtn = document.getElementById('ponto-foto-btn');
  const clockEl = document.getElementById('ponto-clock');
  const nomeInput = document.getElementById('ponto-nome');
  const loginForm = document.getElementById('ponto-login-form');

  let state = {
    id: null,
    nome: '',
    pin: '',
    proxima: 'entrada',
    stream: null,
    blob: null,
  };

  function urlFor(tpl, id) {
    return tpl.replace('/0/', `/${id}/`);
  }

  function updateClock() {
    if (!clockEl) return;
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  updateClock();
  setInterval(updateClock, 15000);

  function maskPin(pin) {
    if (!pin) return '••••';
    return '•'.repeat(Math.min(pin.length, 6));
  }

  function showStep(step) {
    stepAcao.hidden = step !== 'acao';
    stepOk.hidden = step !== 'ok';
  }

  function stopCamera() {
    if (state.stream) {
      state.stream.getTracks().forEach((t) => t.stop());
      state.stream = null;
    }
    video.hidden = true;
  }

  function resetLogin() {
    state.pin = '';
    pinDisplay.textContent = '••••';
    if (nomeInput) nomeInput.value = '';
    pinErro.hidden = true;
  }

  function closeModal() {
    modal.hidden = true;
    stopCamera();
    state = { id: null, nome: '', pin: '', proxima: 'entrada', stream: null, blob: null };
    acaoErro.hidden = true;
    extraToggle.checked = false;
    preview.hidden = true;
    preview.removeAttribute('src');
    showStep('acao');
    resetLogin();
    if (nomeInput) nomeInput.focus();
  }

  function applyFoto(data, nome) {
    if (data.foto_url) {
      fotoEl.src = data.foto_url;
      fotoEl.hidden = false;
      fotoEmpty.hidden = true;
    } else {
      fotoEl.hidden = true;
      fotoEmpty.hidden = false;
      fotoEmpty.textContent = (nome || '?').charAt(0).toUpperCase();
    }
  }

  document.getElementById('ponto-pin-pad').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    if (btn.dataset.digit != null) {
      if (state.pin.length >= 6) return;
      state.pin += btn.dataset.digit;
      pinDisplay.textContent = maskPin(state.pin);
      return;
    }
    if (btn.dataset.action === 'clear') {
      state.pin = '';
      pinDisplay.textContent = '••••';
    }
    if (btn.dataset.action === 'back') {
      state.pin = state.pin.slice(0, -1);
      pinDisplay.textContent = state.pin ? maskPin(state.pin) : '••••';
    }
  });

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    pinErro.hidden = true;
    const nome = (nomeInput.value || '').trim();
    if (nome.length < 2) {
      pinErro.textContent = 'Informe seu nome.';
      pinErro.hidden = false;
      return;
    }
    if (state.pin.length < 4) {
      pinErro.textContent = 'PIN inválido.';
      pinErro.hidden = false;
      return;
    }
    const body = new FormData();
    body.append('nome', nome);
    body.append('pin', state.pin);
    body.append('csrfmiddlewaretoken', csrf);
    try {
      const res = await fetch(autenticarUrl, { method: 'POST', body });
      const data = await res.json();
      if (!data.ok) {
        pinErro.textContent = data.erro || 'Não foi possível entrar.';
        pinErro.hidden = false;
        state.pin = '';
        pinDisplay.textContent = '••••';
        return;
      }
      state.id = data.recreador_id;
      state.nome = data.nome;
      state.proxima = data.proxima_acao;
      nomeEl.textContent = data.nome;
      acaoSugerida.textContent = data.proxima_acao_label;
      applyFoto(data, data.nome);
      showStep('acao');
      modal.hidden = false;
    } catch (err) {
      pinErro.textContent = 'Falha de conexão. Tente de novo.';
      pinErro.hidden = false;
    }
  });

  closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  fotoBtn.addEventListener('click', async () => {
    try {
      if (!state.stream) {
        state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
        video.srcObject = state.stream;
        video.hidden = false;
        fotoBtn.textContent = 'Capturar foto';
        return;
      }
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext('2d').drawImage(video, 0, 0);
      canvas.toBlob((blob) => {
        if (!blob) return;
        state.blob = blob;
        preview.src = URL.createObjectURL(blob);
        preview.hidden = false;
        stopCamera();
        fotoBtn.textContent = 'Tirar outra';
      }, 'image/jpeg', 0.85);
    } catch (err) {
      acaoErro.textContent = 'Câmera indisponível neste dispositivo.';
      acaoErro.hidden = false;
    }
  });

  document.getElementById('ponto-confirmar').addEventListener('click', async () => {
    acaoErro.hidden = true;
    const body = new FormData();
    body.append('pin', state.pin);
    body.append('tipo', state.proxima);
    body.append('extra_plantao', extraToggle.checked ? '1' : '0');
    body.append('csrfmiddlewaretoken', csrf);
    if (state.blob) {
      body.append('foto_auditoria', state.blob, 'batida.jpg');
    }
    try {
      const res = await fetch(urlFor(registrarTpl, state.id), { method: 'POST', body });
      const data = await res.json();
      if (!data.ok) {
        acaoErro.textContent = data.erro || 'Não foi possível registrar.';
        acaoErro.hidden = false;
        return;
      }
      sucessoMsg.textContent = data.mensagem;
      showStep('ok');
      setTimeout(() => {
        closeModal();
        window.location.reload();
      }, 2800);
    } catch (err) {
      acaoErro.textContent = 'Falha de conexão. Tente de novo.';
      acaoErro.hidden = false;
    }
  });
})();

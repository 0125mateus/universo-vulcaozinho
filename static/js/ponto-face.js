/**
 * Reconhecimento facial (face-api) para ponto dos recreadores.
 * Modelos via CDN @vladmandic/face-api.
 */
(function (global) {
  const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/model';
  const SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/dist/face-api.js';

  let modelsReady = null;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (global.faceapi) {
        resolve();
        return;
      }
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('Falha ao carregar face-api.'));
      document.head.appendChild(s);
    });
  }

  async function ensureModels() {
    if (modelsReady) return modelsReady;
    modelsReady = (async () => {
      await loadScript(SCRIPT_URL);
      const faceapi = global.faceapi;
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
        faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
      ]);
      return faceapi;
    })();
    return modelsReady;
  }

  function detectorOptions() {
    return new global.faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.45 });
  }

  async function descriptorFrom(input) {
    const faceapi = await ensureModels();
    const det = await faceapi
      .detectSingleFace(input, detectorOptions())
      .withFaceLandmarks()
      .withFaceDescriptor();
    if (!det) {
      throw new Error('Nenhum rosto detectado. Olhe para a câmera com boa iluminação.');
    }
    return Array.from(det.descriptor);
  }

  global.PontoFace = {
    ensureModels,
    descriptorFrom,
  };
})(window);

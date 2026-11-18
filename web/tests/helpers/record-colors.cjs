// Synthetic browser-encoding fixture; no camera or microphone access.
const { chromium } = require('@playwright/test');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const result = await page.evaluate(async () => {
      const canvas = document.createElement('canvas');
      canvas.width = 480; canvas.height = 240;
      const ctx = canvas.getContext('2d');
      const draw = () => ['red', 'lime', 'blue'].forEach((color, i) => {
        ctx.fillStyle = color; ctx.fillRect(i * 160, 0, 160, 240);
      });
      draw();
      const stream = canvas.captureStream(30);
      const parts = [];
      const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8' });
      const result = new Promise(resolve => {
        recorder.ondataavailable = e => parts.push(e.data);
        recorder.onstop = async () => resolve(Array.from(new Uint8Array(await new Blob(parts).arrayBuffer())));
      });
      const timer = setInterval(draw, 1000 / 30);
      recorder.start(250);
      await new Promise(resolve => setTimeout(resolve, 1200));
      recorder.stop();
      const bytes = await result;
      clearInterval(timer); stream.getTracks().forEach(t => t.stop());
      return bytes;
    });
    fs.writeFileSync(process.argv[2], Buffer.from(result), { mode: 0o600, flag: 'wx' });
  } finally { await browser.close(); }
})().catch(error => { process.stderr.write(error.message); process.exitCode = 1; });

/*! Hubx.Space — Particle Logo Background (vanilla JS)
 *  Portado de particle-logo-background.tsx (React) para uso em Django templates.
 *  Uso: incluir um <canvas id="particle-bg"> antes do #main-content e carregar este script.
 */
(function () {
  "use strict";

  // Config
  const CONFIG = {
    opacity: 0.40,          // também controlado via classe opacity-40 no canvas
    maxConnectionDist: 300, // distância para fade das conexões
    lineWidth: 2,
    instances: (size) => ([ // instâncias do "logo em rede"
      { cx: size.w * 0.20, cy: size.h * 0.30, scale: 0.8, alpha: 0.30 },
      { cx: size.w * 0.80, cy: size.h * 0.70, scale: 1.2, alpha: 0.40 },
      { cx: size.w * 0.60, cy: size.h * 0.20, scale: 0.6, alpha: 0.25 },
      { cx: size.w * 0.10, cy: size.h * 0.80, scale: 0.9, alpha: 0.35 },
      { cx: size.w * 0.90, cy: size.h * 0.40, scale: 0.7, alpha: 0.30 },
    ]),
  };

  // Estrutura do "logo/rede"
  const LOGO_POINTS = [
    { x: 0.5, y: 0.3 }, // top
    { x: 0.3, y: 0.45 }, // top-left
    { x: 0.7, y: 0.45 }, // top-right
    { x: 0.5, y: 0.5 }, // center
    { x: 0.2, y: 0.65 }, // bottom-left
    { x: 0.8, y: 0.65 }, // bottom-right
    { x: 0.35, y: 0.75 }, // bottom-left-inner
    { x: 0.65, y: 0.75 }, // bottom-right-inner
    { x: 0.5, y: 0.8 }, // bottom
  ];

  const LOGO_CONNECTIONS = [
    [0, 3], [1, 3], [2, 3],
    [3, 4], [3, 5], [4, 6], [5, 7], [6, 8], [7, 8],
    [1, 4], [2, 5],
  ];

  // Estado
  let rafId = null;
  let ctx = null;
  let canvas = null;
  const particles = [];
  const connections = [];

  function hslaFromHsl(hsl, alpha) {
    // "hsl(H, S%, L%)" -> "hsla(H, S%, L%, A)"
    return hsl.replace("hsl", "hsla").replace(")", `, ${alpha})`);
  }

  function size() {
    return { w: window.innerWidth, h: window.innerHeight };
  }

  function resizeCanvas() {
    if (!canvas) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function makeScene() {
    particles.length = 0;
    connections.length = 0;

    const s = size();
    const instances = CONFIG.instances(s);

    instances.forEach((inst) => {
      const baseIndex = particles.length;
      LOGO_POINTS.forEach((p) => {
        const baseX = inst.cx + (p.x - 0.5) * 200 * inst.scale;
        const baseY = inst.cy + (p.y - 0.5) * 200 * inst.scale;
        particles.push({
          x: baseX + (Math.random() - 0.5) * 50,
          y: baseY + (Math.random() - 0.5) * 50,
          tx: baseX,
          ty: baseY,
          vx: 0, vy: 0,
          r: 8 + Math.random() * 4,
          o: inst.alpha + Math.random() * 0.2,
          color: `hsl(${200 + Math.random() * 40}, 80%, ${60 + Math.random() * 20}%)`,
        });
      });
      LOGO_CONNECTIONS.forEach(([from, to]) => {
        connections.push({ from: baseIndex + from, to: baseIndex + to, o: inst.alpha * 0.8 });
      });
    });
  }

  function animate(ts) {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const now = Date.now();
    // Atualiza partículas
    for (const p of particles) {
      const dx = p.tx - p.x;
      const dy = p.ty - p.y;
      p.vx += dx * 0.02;
      p.vy += dy * 0.02;
      p.vx *= 0.95;
      p.vy *= 0.95;
      p.x += p.vx;
      p.y += p.vy;
      // Flutuação sutil
      p.tx += Math.sin(now * 0.001 + p.x * 0.01) * 0.5;
      p.ty += Math.cos(now * 0.001 + p.y * 0.01) * 0.5;
    }

    // Conexões
    ctx.lineWidth = CONFIG.lineWidth;
    for (const c of connections) {
      const a = particles[c.from];
      const b = particles[c.to];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.hypot(dx, dy);
      const op = Math.max(0, (CONFIG.maxConnectionDist - dist) / CONFIG.maxConnectionDist) * c.o;
      if (op <= 0.05) continue;
      const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      grad.addColorStop(0, `hsla(210, 80%, 60%, ${op})`);
      grad.addColorStop(0.5, `hsla(220, 90%, 70%, ${op * 1.2})`);
      grad.addColorStop(1, `hsla(230, 80%, 65%, ${op})`);
      ctx.strokeStyle = grad;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    // Partículas
    for (const p of particles) {
      const radial = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r);
      radial.addColorStop(0, hslaFromHsl(p.color, p.o));
      radial.addColorStop(1, hslaFromHsl(p.color, 0));
      ctx.fillStyle = radial;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();

      // Glow interno
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 10;
      ctx.fillStyle = hslaFromHsl(p.color, p.o * 0.8);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 0.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    rafId = requestAnimationFrame(animate);
  }

  function start() {
    if (rafId) cancelAnimationFrame(rafId);
    resizeCanvas();
    makeScene();
    rafId = requestAnimationFrame(animate);
  }

  function stop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  window.addEventListener("DOMContentLoaded", () => {
    canvas = document.getElementById("particle-bg");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
    if (!ctx) return;

    window.addEventListener("resize", () => {
      resizeCanvas();
      // Recria posições alvo ao redimensionar para manter composição
      makeScene();
    });

    start();
  });
})();

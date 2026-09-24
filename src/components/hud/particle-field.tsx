import { useEffect, useRef } from "react";

type Particle = {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  r: number;
  tone: 0 | 1 | 2;
  phase: number;
  speed: number;
};

function seed(count: number): Particle[] {
  const out: Particle[] = [];
  for (let i = 0; i < count; i++) {
    out.push({
      x: (Math.random() - 0.5) * 8,
      y: (Math.random() - 0.5) * 4.4,
      z: Math.random() * 7 + 1.2,
      vx: (Math.random() - 0.5) * 0.004,
      vy: (Math.random() - 0.5) * 0.003,
      vz: (Math.random() - 0.5) * 0.006,
      r: Math.random() * 1.8 + 0.4,
      tone: i % 11 === 0 ? 2 : i % 4 === 0 ? 1 : 0,
      phase: Math.random() * Math.PI * 2,
      speed: 0.4 + Math.random() * 1.4,
    });
  }
  return out;
}

const TONE = [
  [110, 231, 255],
  [222, 244, 255],
  [240, 198, 116],
] as const;

export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const node = canvasRef.current;
    if (!node) return;
    const surface: HTMLCanvasElement = node;
    const ctx = surface.getContext("2d", { alpha: true });
    if (!ctx) return;
    const g: CanvasRenderingContext2D = ctx;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const mobile = window.matchMedia("(max-width: 720px)").matches;
    const count = reduce ? 16 : mobile ? 46 : 96;
    const particles = seed(count);

    let w = 0;
    let h = 0;
    let dpr = 1;
    let raf = 0;
    let running = true;
    const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
    let rot = 0;

    function resize() {
      const rect = surface.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      w = Math.max(1, Math.floor(rect.width));
      h = Math.max(1, Math.floor(rect.height));
      surface.width = Math.floor(w * dpr);
      surface.height = Math.floor(h * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function onMove(event: PointerEvent) {
      const rect = surface.getBoundingClientRect();
      mouse.tx = ((event.clientX - rect.left) / rect.width - 0.5) * 1.4;
      mouse.ty = ((event.clientY - rect.top) / rect.height - 0.5) * 0.9;
    }

    function draw(now: number) {
      if (!running) return;
      raf = window.requestAnimationFrame(draw);
      const t = now * 0.001;
      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;
      rot += reduce ? 0 : 0.00055;

      g.clearRect(0, 0, w, h);
      const fov = Math.min(w, h) * 0.72;
      const cos = Math.cos(rot);
      const sin = Math.sin(rot);

      for (const p of particles) {
        if (!reduce) {
          p.x += p.vx * p.speed;
          p.y += p.vy * p.speed;
          p.z += p.vz * p.speed;
          if (p.x > 4.2 || p.x < -4.2) p.vx *= -1;
          if (p.y > 2.4 || p.y < -2.4) p.vy *= -1;
          if (p.z > 8.2 || p.z < 1.1) p.vz *= -1;
        }

        const rx = p.x * cos - p.z * sin;
        const rz = p.x * sin + p.z * cos;
        const ry = p.y + Math.sin(t * 0.35 + p.phase) * 0.08;
        const z = rz + 5.2;
        const scale = fov / z;
        const sx = w * 0.5 + (rx + mouse.x * 0.55) * scale;
        const sy = h * 0.48 + (ry + mouse.y * 0.4) * scale;
        const pulse = 0.55 + Math.sin(t * 1.6 + p.phase) * 0.45;
        const size = Math.max(0.35, p.r * scale * 0.085) * (0.7 + pulse * 0.4);
        const depth = Math.min(1, 1.8 / z);
        const [cr, cg, cb] = TONE[p.tone];
        const alpha = 0.12 + depth * 0.78 * pulse;

        if (sx < -20 || sy < -20 || sx > w + 20 || sy > h + 20) continue;

        const glow = g.createRadialGradient(sx, sy, 0, sx, sy, size * 4.2);
        glow.addColorStop(0, `rgba(${cr},${cg},${cb},${alpha})`);
        glow.addColorStop(0.28, `rgba(${cr},${cg},${cb},${alpha * 0.35})`);
        glow.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
        g.fillStyle = glow;
        g.beginPath();
        g.arc(sx, sy, size * 4.2, 0, Math.PI * 2);
        g.fill();

        g.fillStyle = `rgba(${cr},${cg},${cb},${Math.min(1, alpha + 0.15)})`;
        g.beginPath();
        g.arc(sx, sy, size, 0, Math.PI * 2);
        g.fill();
      }
    }

    function onVis() {
      running = document.visibilityState === "visible";
      if (running) raf = window.requestAnimationFrame(draw);
      else window.cancelAnimationFrame(raf);
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("visibilitychange", onVis);
    raf = window.requestAnimationFrame(draw);

    return () => {
      running = false;
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
    />
  );
}

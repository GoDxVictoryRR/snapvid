/**
 * SnapVid Studio — Google Antigravity Interactive Particle Background
 * 
 * Standalone background engine inspired by Google Antigravity hero background:
 * - Dispersed field of tiny dash/capsule-shaped particles (confetti/streaks).
 * - Subtle multi-colored Google palette accents (Blue, Red, Yellow, Green, Purple, Coral).
 * - Smooth mouse cursor tracking (100px - 150px repulsion force field).
 * - Dynamic velocity alignment (capsules rotate along movement vector).
 * - Damping spring return physics & natural gentle idle breathing drift.
 * - Hardware-accelerated 60fps canvas with HiDPI / Retina display support.
 * - Theme-reactive (instant adapt between Dark Obsidian and Light Alabaster).
 */

(function () {
  "use strict";

  // Google Antigravity authentic palette accents
  const PALETTES = {
    dark: [
      { color: "#4285F4", alpha: 0.72 }, // Google Blue
      { color: "#8AB4F8", alpha: 0.85 }, // Pastel Blue
      { color: "#EA4335", alpha: 0.72 }, // Google Red
      { color: "#F28B82", alpha: 0.85 }, // Pastel Red
      { color: "#FBBC04", alpha: 0.78 }, // Google Yellow / Amber
      { color: "#FDD663", alpha: 0.88 }, // Pastel Yellow
      { color: "#34A853", alpha: 0.72 }, // Google Green
      { color: "#81C995", alpha: 0.85 }, // Pastel Green
      { color: "#A142F4", alpha: 0.70 }, // Google Purple
      { color: "#C58AF9", alpha: 0.85 }, // Pastel Violet
      { color: "#FA7B17", alpha: 0.75 }, // Google Orange / Coral
    ],
    light: [
      { color: "#1A73E8", alpha: 0.75 }, // Vibrant Google Blue
      { color: "#D93025", alpha: 0.75 }, // Vibrant Google Red
      { color: "#E37400", alpha: 0.80 }, // Saturated Amber
      { color: "#188038", alpha: 0.75 }, // Vibrant Green
      { color: "#9334E6", alpha: 0.75 }, // Vibrant Purple
      { color: "#E8710A", alpha: 0.75 }, // Vibrant Orange
      { color: "#1967D2", alpha: 0.70 }, // Deep Blue
      { color: "#C5221F", alpha: 0.70 }, // Deep Red
      { color: "#137333", alpha: 0.70 }, // Deep Green
    ]
  };

  class AntigravityBackground {
    constructor() {
      this.canvas = document.getElementById("antigravity-canvas");
      if (!this.canvas) {
        this.canvas = document.createElement("canvas");
        this.canvas.id = "antigravity-canvas";
        this.canvas.className = "antigravity-canvas";
        this.canvas.setAttribute("aria-hidden", "true");
        this.canvas.style.cssText = "position: fixed; inset: 0; pointer-events: none; z-index: -1; width: 100vw; height: 100vh; display: block;";
        document.body.prepend(this.canvas);
      }

      this.ctx = this.canvas.getContext("2d");
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.width = window.innerWidth;
      this.height = window.innerHeight;

      // Mouse tracking state
      this.mouse = {
        x: -9999,
        y: -9999,
        prevX: -9999,
        prevY: -9999,
        vx: 0,
        vy: 0,
        speed: 0,
        active: false,
        radius: 135, // 100px - 150px repulsion field
      };

      this.particles = [];
      this.startTime = performance.now();
      this.lastTime = this.startTime;
      this.currentTheme = this.detectTheme();

      this.initEvents();
      this.resize();
      this.spawnParticles();
      this.animate();
    }

    detectTheme() {
      const theme = document.documentElement.getAttribute("data-theme") || 
                    document.body.getAttribute("data-theme") || 
                    localStorage.getItem("snapvid_theme") || 
                    "dark";
      return theme === "light" ? "light" : "dark";
    }

    initEvents() {
      // Window resize
      window.addEventListener("resize", () => this.resize(), { passive: true });

      // Smooth mouse tracking
      const onPointerMove = (e) => {
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;

        if (this.mouse.active) {
          this.mouse.vx = (clientX - this.mouse.prevX) * 0.4;
          this.mouse.vy = (clientY - this.mouse.prevY) * 0.4;
          this.mouse.speed = Math.hypot(this.mouse.vx, this.mouse.vy);
        } else {
          this.mouse.vx = 0;
          this.mouse.vy = 0;
          this.mouse.speed = 0;
        }

        this.mouse.prevX = clientX;
        this.mouse.prevY = clientY;
        this.mouse.x = clientX;
        this.mouse.y = clientY;
        this.mouse.active = true;
      };

      const onPointerLeave = () => {
        this.mouse.active = false;
        this.mouse.x = -9999;
        this.mouse.y = -9999;
        this.mouse.vx = 0;
        this.mouse.vy = 0;
        this.mouse.speed = 0;
      };

      window.addEventListener("mousemove", onPointerMove, { passive: true });
      window.addEventListener("touchmove", onPointerMove, { passive: true });
      window.addEventListener("mouseleave", onPointerLeave, { passive: true });
      window.addEventListener("touchend", onPointerLeave, { passive: true });

      // Theme change observer
      const observer = new MutationObserver(() => {
        const newTheme = this.detectTheme();
        if (newTheme !== this.currentTheme) {
          this.currentTheme = newTheme;
          this.updatePaletteColors();
        }
      });

      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      observer.observe(document.body, { attributes: true, attributeFilter: ["data-theme"] });
    }

    resize() {
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.width = window.innerWidth;
      this.height = window.innerHeight;

      this.canvas.width = Math.floor(this.width * this.dpr);
      this.canvas.height = Math.floor(this.height * this.dpr);
      this.canvas.style.width = this.width + "px";
      this.canvas.style.height = this.height + "px";

      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.scale(this.dpr, this.dpr);

      // Re-anchor existing particles proportionally
      if (this.particles.length > 0) {
        const count = this.getDesiredParticleCount();
        if (Math.abs(count - this.particles.length) > 40) {
          this.spawnParticles();
        } else {
          this.particles.forEach((p) => {
            p.homeX = p.relX * this.width;
            p.homeY = p.relY * this.height;
          });
        }
      }
    }

    getDesiredParticleCount() {
      // Density tuned for silky 60fps & true Antigravity aesthetic
      const area = this.width * this.height;
      return Math.max(140, Math.min(260, Math.floor(area / 6500)));
    }

    spawnParticles() {
      const count = this.getDesiredParticleCount();
      const palette = PALETTES[this.currentTheme];
      this.particles = [];

      // Hero center attractor for Antigravity orbital flow curvature
      const centerX = this.width * 0.52;
      const centerY = this.height * 0.38;

      for (let i = 0; i < count; i++) {
        // Distribute in a dynamic sweeping field with gentle spiral bias
        const isOrbitFlow = Math.random() < 0.65;
        let x, y, baseAngle;

        if (isOrbitFlow) {
          // Flow field sweeping around hero section
          const angle = Math.random() * Math.PI * 2;
          const dist = 80 + Math.pow(Math.random(), 0.8) * Math.max(this.width, this.height) * 0.65;
          x = centerX + Math.cos(angle) * dist * 1.35;
          y = centerY + Math.sin(angle) * dist * 0.85;

          // Flow stream tangent orientation
          const tangent = angle + Math.PI * 0.5;
          baseAngle = tangent + (Math.random() - 0.5) * 0.4;
        } else {
          // Uniform scattered field
          x = Math.random() * this.width;
          y = Math.random() * this.height;
          baseAngle = (Math.random() - 0.5) * Math.PI;
        }

        const colorItem = palette[i % palette.length];
        const length = 7.5 + Math.random() * 8.5; // 8px - 16px capsule length
        const thickness = 2.0 + Math.random() * 1.4; // 2px - 3.4px capsule width

        this.particles.push({
          relX: x / Math.max(this.width, 1),
          relY: y / Math.max(this.height, 1),
          homeX: x,
          homeY: y,
          x: x,
          y: y,
          vx: 0,
          vy: 0,
          length: length,
          thickness: thickness,
          baseAngle: baseAngle,
          angle: baseAngle,
          targetAngle: baseAngle,
          colorIndex: i % palette.length,
          color: colorItem.color,
          baseAlpha: colorItem.alpha,
          currentAlpha: colorItem.alpha,
          driftSpeed: 0.35 + Math.random() * 0.45,
          driftPhase: Math.random() * Math.PI * 2,
          driftRadiusX: 10 + Math.random() * 18,
          driftRadiusY: 8 + Math.random() * 14,
        });
      }
    }

    updatePaletteColors() {
      const palette = PALETTES[this.currentTheme];
      this.particles.forEach((p) => {
        const item = palette[p.colorIndex % palette.length];
        p.color = item.color;
        p.baseAlpha = item.alpha;
      });
    }

    animate() {
      requestAnimationFrame(() => this.animate());

      const now = performance.now();
      const dt = Math.min((now - this.lastTime) / 1000, 0.05); // Cap delta to avoid leaps
      this.lastTime = now;
      const elapsed = (now - this.startTime) / 1000;

      // Clear full canvas with crisp transparency
      this.ctx.clearRect(0, 0, this.width, this.height);

      const mouse = this.mouse;
      const radiusSq = mouse.radius * mouse.radius;

      // Physics loop
      for (let i = 0; i < this.particles.length; i++) {
        const p = this.particles[i];

        // 1. Natural idle breathing drift anchor
        const idleX = p.homeX + Math.cos(elapsed * p.driftSpeed + p.driftPhase) * p.driftRadiusX;
        const idleY = p.homeY + Math.sin(elapsed * (p.driftSpeed * 0.85) + p.driftPhase) * p.driftRadiusY;

        // 2. Mouse Repulsion Force Field
        if (mouse.active) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const distSq = dx * dx + dy * dy;

          if (distSq < radiusSq && distSq > 0.01) {
            const dist = Math.sqrt(distSq);
            const norm = 1 - dist / mouse.radius;
            // Responsive cubic push outward
            const force = Math.pow(norm, 1.6) * 13.5;

            const pushX = (dx / dist) * force;
            const pushY = (dy / dist) * force;

            p.vx += pushX;
            p.vy += pushY;

            // Lateral momentum drag from fast cursor sweep
            if (mouse.speed > 1.2) {
              const drag = Math.min(mouse.speed * 0.1, 3.5) * norm;
              p.vx += mouse.vx * drag;
              p.vy += mouse.vy * drag;
            }
          }
        }

        // 3. Spring-damper return towards idle anchor
        const springK = 0.034;
        const damping = 0.885;

        const ax = (idleX - p.x) * springK;
        const ay = (idleY - p.y) * springK;

        p.vx = (p.vx + ax) * damping;
        p.vy = (p.vy + ay) * damping;

        p.x += p.vx;
        p.y += p.vy;

        // 4. Dynamic Velocity Alignment (Rotation)
        const speed = Math.hypot(p.vx, p.vy);
        if (speed > 0.35) {
          // Align capsule orientation dynamically along movement trajectory
          p.targetAngle = Math.atan2(p.vy, p.vx);
        } else {
          // Return smoothly to natural flow stream angle
          p.targetAngle = p.baseAngle + Math.sin(elapsed * 0.6 + p.driftPhase) * 0.22;
        }

        // Shortest angular distance interpolation
        let angleDiff = p.targetAngle - p.angle;
        while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
        while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        p.angle += angleDiff * Math.min(0.18 + speed * 0.03, 0.45);

        // 5. Render Capsule / Dash Streak
        this.ctx.save();
        this.ctx.translate(p.x, p.y);
        this.ctx.rotate(p.angle);

        // Capsule length extends slightly with velocity for streak effect
        const dynamicLen = p.length + Math.min(speed * 1.8, 12);

        this.ctx.beginPath();
        this.ctx.lineCap = "round";
        this.ctx.lineWidth = p.thickness;
        this.ctx.strokeStyle = p.color;
        this.ctx.globalAlpha = p.baseAlpha;
        this.ctx.moveTo(-dynamicLen * 0.5, 0);
        this.ctx.lineTo(dynamicLen * 0.5, 0);
        this.ctx.stroke();

        this.ctx.restore();
      }

      // Decay mouse velocity gradually between frames
      mouse.vx *= 0.85;
      mouse.vy *= 0.85;
      mouse.speed *= 0.85;
    }
  }

  // Auto-init on DOM readiness
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => new AntigravityBackground());
  } else {
    new AntigravityBackground();
  }
})();

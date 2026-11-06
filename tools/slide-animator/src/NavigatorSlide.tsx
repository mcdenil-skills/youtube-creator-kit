import React, { useRef, useLayoutEffect } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { SPEED, REVEAL_DUR } from "./timing";

// stagger: первый блок стартует на BASE, каждый следующий +STEP секунд (до умножения на SPEED)
const BASE = 0.15;
const STEP = 0.25;

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
// приближение cubic-bezier(.16,1,.3,1) — быстрый старт, мягкий доводчик
const easeOut = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));

export type NavProps = { css: string; stageHtml: string; durationInFrames: number; layer: string | null };

export const NavigatorSlide: React.FC<NavProps> = ({ css, stageHtml, layer }) => {
  const ref = useRef<HTMLDivElement>(null);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const stage = el.querySelector(".stage") as HTMLElement | null;
    const nodes = el.querySelectorAll<HTMLElement>("[data-anim-id]");

    // ── Режим слоя: статика, виден только целевой блок (для прозрачных PNG) ──
    if (layer !== null) {
      if (layer === "bg") {
        nodes.forEach((n) => (n.style.visibility = "hidden"));
      } else {
        if (stage) stage.style.background = "transparent";
        nodes.forEach((n) => {
          const on = n.dataset.animId === layer;
          n.style.visibility = on ? "visible" : "hidden";
          n.style.opacity = "1";
          n.style.transform = "none";
        });
      }
      return;
    }

    // ── Полный режим: каскадное появление по кадрам ──
    nodes.forEach((n) => {
      const i = Number(n.dataset.animId);
      const delay = (BASE + i * STEP) * SPEED * fps;
      const dur = REVEAL_DUR * SPEED * fps;
      const t = easeOut(clamp01((frame - delay) / dur));
      n.style.opacity = String(t);
      n.style.transform = `translateY(${(1 - t) * 28}px)`;
    });
  }, [frame, layer, fps, stageHtml]);

  const showBg = layer === null || layer === "bg";
  return (
    <AbsoluteFill style={{ background: showBg ? "#1E1E1E" : "transparent" }}>
      {/* CSS презентации + сброс встроенного scroll-reveal (в Remotion анимируем по кадрам,
          а не CSS-переходами) + растяжка .stage на весь кадр. Идёт после CSS слайда —
          перекрывает базовый opacity:0; наш inline по кадрам перекрывает уже этот сброс. */}
      <style dangerouslySetInnerHTML={{ __html:
        css + "\nhtml,body{background:transparent!important;}" +
        "\n.stage-inner > *, .stage-inner .flow > *, .stage-inner .duo > *," +
        ".stage-inner .points > *, .stage-inner .body-grid > * {" +
        "opacity:1; transform:none; transition:none;}" +
        "\n.stage{width:100%!important;height:100%!important;}"
      }} />
      <div ref={ref} style={{ width: "100%", height: "100%" }} dangerouslySetInnerHTML={{ __html: stageHtml }} />
    </AbsoluteFill>
  );
};

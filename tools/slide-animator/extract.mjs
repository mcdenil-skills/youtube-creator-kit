import { parse } from "node-html-parser";

const SPEED = 1.5;
const REVEAL_DUR = 0.5;
const BASE = 0.15;
const STEP = 0.25;
const FPS = 30;
const CONTAINERS = ["flow", "duo", "points", "body-grid"];

export function extractDeck(html) {
  const root = parse(html, { comment: false });
  const css = root.querySelectorAll("style").map((style) => style.text).join("\n");
  const slides = root.querySelectorAll("section.slide");
  if (!slides.length) throw new Error("Не найдено слайдов в navigator.html");

  return slides.map((section, index) => {
    const stage = section.querySelector(".stage");
    if (!stage) throw new Error(`Слайд ${index + 1}: отсутствует зона зрителя .stage`);
    const inner = stage.querySelector(".stage-inner") || stage;
    const layers = [];
    for (const child of inner.children) {
      const grouped = CONTAINERS.some((name) => child.classList.contains(name));
      const elements = grouped && child.children.length ? child.children : [child];
      for (const element of elements) {
        const id = layers.length;
        element.setAttribute("data-anim-id", String(id));
        const label = element.rawTagName.toLowerCase();
        layers.push({ id, name: `${String(id + 1).padStart(2, "0")}-${label}` });
      }
    }
    if (!layers.length) throw new Error(`Слайд ${index + 1}: нет элементов для анимации`);
    const seconds = (BASE + (layers.length - 1) * STEP + REVEAL_DUR) * SPEED + 1.6;
    return { css, stageHtml: stage.toString(), layers, durationInFrames: Math.round(seconds * FPS) };
  });
}

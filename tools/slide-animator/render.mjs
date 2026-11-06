import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { extractDeck } from "./extract.mjs";

async function main() {
  const [file, ...selection] = process.argv.slice(2);
  if (!file || file === "--help") {
    console.log("node tools/slide-animator/render.mjs ПАПКА/navigator.html [номер слайда ...]");
    return;
  }
  const slides = extractDeck(await readFile(file, "utf-8"));
  const indices = selection.length ? [...new Set(selection.map(Number))] : slides.map((_, i) => i + 1);
  if (indices.some((index) => !Number.isInteger(index) || index < 1 || index > slides.length)) {
    throw new Error(`Номера слайдов должны быть от 1 до ${slides.length}`);
  }
  const dest = resolve(file, "..", "animation");
  const temp = await mkdtemp(join(tmpdir(), "creator-render-"));
  let browser;
  try {
    const serveUrl = await bundle({
      entryPoint: fileURLToPath(new URL("src/index.ts", import.meta.url)),
      outDir: temp,
    });
    browser = await openBrowser("chrome", {
      browserExecutable: process.env.REMOTION_BROWSER_EXECUTABLE || null,
      logLevel: "warn",
    });
    const common = { serveUrl, puppeteerInstance: browser, logLevel: "warn" };
    const select = (inputProps) => selectComposition({ ...common, id: "NavigatorSlide", inputProps });
    for (const index of indices) {
      const { layers, ...slide } = slides[index - 1];
      const suffix = String(index).padStart(2, "0");
      const label = `slide-${suffix}`;
      const composition = await select({ ...slide, layer: null });
      await Promise.all(["full", "poster", `layers/${label}`].map((name) =>
        mkdir(join(dest, name), { recursive: true })));
      await renderMedia({
        ...common, composition, codec: "h264", concurrency: 2,
        inputProps: { ...slide, layer: null },
        outputLocation: join(dest, "full", `${label}.mp4`),
      });
      const still = async (path, layer) => {
        const inputProps = { ...slide, layer };
        // The renderer uses the resolved props on the selected composition.
        const stillComposition = layer === null ? composition : await select(inputProps);
        await renderStill({
          ...common, composition: stillComposition, frame: composition.durationInFrames - 1,
          imageFormat: "png", inputProps, output: join(dest, path),
        });
      };
      await still(`poster/${label}.png`, null);
      await still(`layers/${label}/00-bg.png`, "bg");
      for (const layer of layers) {
        await still(`layers/${label}/${layer.name}.png`, String(layer.id));
      }
      console.log(`${label}: MP4, постер, фон и ${layers.length} слоёв`);
    }
  } finally {
    try {
      await browser?.close({ silent: true });
    } finally {
      await rm(temp, { recursive: true, force: true });
    }
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});

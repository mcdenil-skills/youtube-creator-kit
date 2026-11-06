import assert from "node:assert/strict";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const directory = resolve(process.argv[2] ?? fileURLToPath(new URL("../../examples/demo/", import.meta.url)));
const url = (name) => pathToFileURL(resolve(directory, name)).href;
const browser = await chromium.launch({
  executablePath: process.env.CHROME_PATH || undefined,
  headless: true,
});
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(url("navigator.html"));
  const slides = page.locator("section.slide");
  const count = await slides.count();
  assert.ok(count >= 2);
  assert.equal(await page.locator("#position").textContent(), `1 / ${count}`);
  const overflow = await page.evaluate(() => {
    const layout = [...document.querySelectorAll(".slide")].map((slide) => {
      const stage = slide.querySelector(".stage");
      const cheat = slide.querySelector(".cheat");
      return [
        stage.offsetWidth,
        cheat.offsetWidth,
        stage.scrollHeight <= stage.clientHeight,
        cheat.scrollHeight <= cheat.clientHeight,
        stage.scrollWidth <= stage.clientWidth,
        cheat.scrollWidth <= cheat.clientWidth,
      ];
    });
    return { layout, pageFits: document.documentElement.scrollWidth === innerWidth };
  });
  assert.ok(overflow.pageFits);
  for (const row of overflow.layout) assert.deepEqual(row, [1440, 480, true, true, true, true]);
  await page.keyboard.press("ArrowRight");
  assert.equal(await page.locator("#position").textContent(), `2 / ${count}`);
  await page.keyboard.press("End");
  assert.equal(await page.locator("#position").textContent(), `${count} / ${count}`);
  await page.locator("#previous").click();
  assert.equal(await page.locator("#position").textContent(), `${count - 1} / ${count}`);

  await page.goto(url("teleprompter.html"));
  await page.locator("#play").click();
  await page.waitForFunction(() => scrollY > 10);
  await page.locator("#play").click();
  assert.equal(await page.locator("#play").textContent(), "Пуск");
  await page.locator("#mirror").check();
  assert.equal(await page.locator("main").getAttribute("class"), "mirrored");
  await page.locator("#size").fill("68");
  assert.equal(await page.locator("main").evaluate((main) => getComputedStyle(main).fontSize), "68px");
  await page.locator("#reset").click();
  await page.waitForFunction(() => scrollY === 0);
  assert.deepEqual(errors, []);
  console.log(`Chromium 1920×1080: ${count} слайда без переполнений, навигация и суфлёр работают.`);
} finally {
  await browser.close();
}

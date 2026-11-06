import assert from "node:assert/strict";
import test from "node:test";
import { extractDeck } from "./extract.mjs";

test("extracts audience layers without speaker notes", () => {
  const [slide] = extractDeck(`
    <style>.stage{color:white}</style>
    <section class="slide">
      <div class="stage"><div class="stage-inner">
        <h2>Visible</h2><ol class="points"><li>First</li><li>Second</li></ol>
      </div></div>
      <aside class="cheat">Private speaker cues</aside>
    </section>`);
  assert.equal(slide.css, ".stage{color:white}");
  assert.equal(slide.layers.length, 3);
  assert.match(slide.stageHtml, /data-anim-id="2"/);
  assert.doesNotMatch(slide.stageHtml, /speaker cues/);
  assert.ok(slide.durationInFrames > 30);
});

test("rejects an incomplete slide instead of changing slide numbering", () => {
  assert.throws(() => extractDeck('<section class="slide"></section>'), /слайд 1/i);
  assert.throws(() => extractDeck("<p>Other page</p>"), /не найдено/i);
});

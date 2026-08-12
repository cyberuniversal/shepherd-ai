import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";
import sharp from "sharp";

const ROOT = "D:/Users/momoa/Desktop/shepherd-ai";
const OUT = path.join(ROOT, "reports", "final");
const PREVIEW = path.join(OUT, "presentation_preview");
const W = 1280;
const H = 720;
const C = {
  bg: "#F4F7F6",
  paper: "#FFFFFF",
  ink: "#17212B",
  muted: "#5F6D78",
  teal: "#0F5C5E",
  teal2: "#2E7B7A",
  mint: "#DCE9E7",
  line: "#CDD7D8",
  red: "#B4483E",
  redSoft: "#F2DEDA",
  gold: "#D9A72E",
};

await fs.mkdir(PREVIEW, { recursive: true });
const deck = Presentation.create({ slideSize: { width: W, height: H } });

function box(slide, x, y, w, h, fill, radius = 0, line = "none") {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius ? { borderRadius: "rounded-lg" } : {}),
  });
}

function text(slide, value, x, y, w, h, size = 20, color = C.ink, bold = false, align = "left") {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = { fontSize: size, color, bold, alignment: align, fontFamily: "Aptos" };
  return shape;
}

function title(slide, value, kicker = "SHEPHERD-AI") {
  text(slide, kicker, 72, 38, 300, 24, 13, C.teal, true);
  text(slide, value, 72, 72, 1136, 58, 36, C.ink, true);
  box(slide, 72, 142, 88, 4, C.red);
}

function footer(slide, source, number) {
  box(slide, 72, 676, 1136, 1, C.line);
  text(slide, source, 72, 684, 1020, 20, 10, C.muted, false);
  text(slide, String(number).padStart(2, "0"), 1150, 682, 58, 20, 11, C.muted, true, "right");
}

async function image(slide, rel, x, y, w, h, alt) {
  const bytes = await fs.readFile(path.join(ROOT, rel));
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
  });
}

function arrow(slide, x, y, w) {
  box(slide, x, y + 8, w - 16, 3, C.teal2);
  const head = slide.shapes.add({
    geometry: "triangle",
    position: { left: x + w - 20, top: y, width: 18, height: 18 },
    fill: C.teal2,
    line: { style: "solid", fill: C.teal2, width: 0 },
    rotation: 90,
  });
  return head;
}

// 1. Title
{
  const s = deck.slides.add();
  s.background.fill = C.teal;
  box(s, 0, 0, 18, H, C.red);
  text(s, "VALIDATION PLACEMENT IN LOCAL MULTI-UAV LANGUAGE PLANNING", 76, 74, 790, 32, 15, C.mint, true);
  text(s, "When should a language planner be stopped?", 76, 150, 970, 132, 52, C.paper, true);
  text(s, "A paired safety, utility, and compute study", 78, 310, 760, 44, 25, C.mint, false);
  box(s, 78, 400, 650, 2, C.mint);
  text(s, "Qwen2.5 3B + 7B  |  11,360 accuracy rows  |  3,600 resource rows", 78, 426, 920, 30, 18, C.paper, true);
  text(s, "Final mentor-review package  |  12 August 2026", 78, 616, 620, 24, 14, C.mint, false);
}

// 2. Problem
{
  const s = deck.slides.add(); s.background.fill = C.bg;
  title(s, "A valid-looking plan can still act on missing evidence");
  text(s, "Language models can produce structured, fluent plans even when a required fact is absent, a resource is unavailable, or a parameter is unsupported.", 72, 188, 530, 150, 27, C.ink, true);
  text(s, "The study asks whether moving validation earlier changes where those failures are contained, without assuming operational execution.", 72, 374, 510, 104, 20, C.muted);
  const ys = [198, 310, 422];
  const labels = [
    ["MISSING", "required mission fact"],
    ["CONFLICTING", "resource or state evidence"],
    ["UNSUPPORTED", "endpoint or parameter"],
  ];
  for (let i = 0; i < 3; i++) {
    box(s, 690, ys[i], 430, 78, i === 1 ? C.redSoft : C.mint, 8, i === 1 ? C.red : C.teal2);
    text(s, labels[i][0], 716, ys[i] + 14, 150, 25, 15, i === 1 ? C.red : C.teal, true);
    text(s, labels[i][1], 716, ys[i] + 40, 350, 24, 18, C.ink);
  }
  footer(s, "Final manuscript, Sections 1-2", 2);
}

// 3. Design
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "The frozen design pairs every method on the same source tasks");
  const metrics = [
    ["75", "source sessions"], ["1,500", "official tasks"], ["284", "held-out clusters"],
    ["1,420", "cases per method"], ["2", "model scales"], ["4", "methods"],
  ];
  for (let i = 0; i < metrics.length; i++) {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 88 + col * 386, y = 190 + row * 180;
    text(s, metrics[i][0], x, y, 260, 70, 47, i === 3 ? C.red : C.teal, true);
    text(s, metrics[i][1], x, y + 70, 275, 34, 18, C.muted);
    if (col < 2) box(s, x + 300, y + 8, 1, 100, C.line);
  }
  text(s, "Five linked variants stay together: canonical execute, official alias, missing-information clarify, restored-information execute, and resource-conflict block.", 88, 548, 1090, 70, 21, C.ink, true);
  footer(s, "datasets/multiuav_plat/accuracy_protocol_freeze_v1.json | [E4] MultiUAV-Plat", 3);
}

// 4. Pipeline
{
  const s = deck.slides.add(); s.background.fill = C.bg;
  title(s, "The final paper is a text-first, static-fidelity experiment");
  const labels = ["Pinned source", "Controlled variants", "M1-M4", "Strict parsing", "Deterministic validators", "Scoring + bootstrap"];
  for (let i = 0; i < labels.length; i++) {
    const x = 58 + i * 202;
    box(s, x, 260, 166, 118, i === 2 ? C.redSoft : C.paper, 8, i === 2 ? C.red : C.line);
    text(s, String(i + 1), x + 16, 276, 30, 24, 14, i === 2 ? C.red : C.teal, true);
    text(s, labels[i], x + 16, 318, 134, 46, 18, C.ink, true, "center");
    if (i < labels.length - 1) arrow(s, x + 168, 309, 34);
  }
  text(s, "Not in the final M1-M4 path", 72, 462, 300, 30, 17, C.red, true);
  text(s, "Whisper speech input  |  DistilBERT span tagging  |  Week 6 vision", 72, 506, 820, 38, 24, C.ink, true);
  text(s, "Preserved as preliminary roadmap work; excluded from primary claims.", 72, 552, 780, 28, 18, C.muted);
  footer(s, "docs/final_pipeline_architecture.md", 4);
}

// 5. Methods
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "Validation placement is the controlled architectural variable");
  const methods = [
    ["M1", "Monolithic", "One call produces decision + plan", C.red],
    ["M2", "Post-plan", "One call, then deterministic gate", C.teal2],
    ["M3", "Stage-wise", "Evidence decision, validate, then plan", C.teal],
    ["M4", "Model-call-count-matched", "Two calls, validation after planning", C.gold],
  ];
  for (let i = 0; i < methods.length; i++) {
    const x = 70 + i * 300;
    box(s, x, 204, 264, 8, methods[i][3]);
    text(s, methods[i][0], x, 235, 264, 44, 30, methods[i][3], true);
    text(s, methods[i][1], x, 294, 264, 66, i === 3 ? 18 : 23, C.ink, true);
    text(s, methods[i][2], x, 385, 248, 86, 18, C.muted);
    text(s, i < 2 ? "1 model call" : "2 model calls", x, 514, 248, 26, 16, C.ink, true);
  }
  footer(s, "src/shepherd_ai/multiuav_methods.py | src/shepherd_ai/multiuav_prompts.py", 5);
}

// 6. Accuracy
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "Stage-wise validation improves containment, especially at 7B");
  await image(s, "reports/figures/multiuav_accuracy_primary_outcomes_v1.png", 76, 164, 1128, 474, "Registered primary accuracy outcomes by model and method");
  footer(s, "outputs/tables/multiuav_accuracy_primary_rates_v1.csv", 6);
}

// 7. Negative result
{
  const s = deck.slides.add(); s.background.fill = C.bg;
  title(s, "Containment improved; executable static plan fidelity did not");
  text(s, "0 / 852", 78, 194, 470, 104, 68, C.red, true);
  text(s, "executable cases achieved static plan fidelity", 82, 304, 500, 72, 24, C.ink, true);
  box(s, 620, 186, 2, 350, C.line);
  text(s, "7B M3", 680, 198, 210, 40, 24, C.teal, true);
  text(s, "0 unsafe proceeds", 680, 254, 410, 34, 27, C.ink, true);
  text(s, "in 568 non-executable cases", 680, 292, 420, 26, 18, C.muted);
  text(s, "228 strict successes", 680, 368, 410, 34, 27, C.ink, true);
  text(s, "all were containment outcomes", 680, 406, 430, 26, 18, C.muted);
  text(s, "Session check", 82, 488, 180, 26, 16, C.teal, true);
  text(s, "M3 contained every non-executable case in all 15 held-out sessions for both model sizes.", 82, 526, 1020, 56, 22, C.ink, true);
  footer(s, "reports/multiuav_accuracy_failure_analysis_v1.md", 7);
}

// 8. Accuracy contrasts
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "The 7B contrast improves both registered outcomes");
  await image(s, "reports/figures/multiuav_accuracy_registered_contrasts_v1.png", 84, 164, 1112, 472, "Registered M3 paired contrasts with 95 percent bootstrap intervals");
  footer(s, "outputs/tables/multiuav_accuracy_registered_contrasts_v1.csv", 8);
}

// 9. Resource M1
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "Resource effects reverse between 3B and 7B against M1");
  await image(s, "reports/figures/multiuav_resource_m3_minus_m1_v1.png", 86, 156, 1110, 486, "Exploratory M3 minus M1 resource contrasts");
  footer(s, "outputs/tables/multiuav_resource_contrasts_v1.csv | RTX 3090 attempt 3", 9);
}

// 10. Resource M4
{
  const s = deck.slides.add(); s.background.fill = C.paper;
  title(s, "Equal model-call counts do not imply equal compute");
  await image(s, "reports/figures/multiuav_resource_m3_minus_m4_v1.png", 86, 156, 1110, 486, "Exploratory M3 minus M4 resource contrasts");
  footer(s, "M4 is model-call-count-matched only; tokens, latency, memory, and energy remain outcomes", 10);
}

// 11. Close
{
  const s = deck.slides.add(); s.background.fill = C.teal;
  text(s, "WHAT THE COMPLETED STUDY SUPPORTS", 76, 56, 600, 24, 14, C.mint, true);
  text(s, "A narrow, reproducible result", 76, 102, 780, 62, 40, C.paper, true);
  const items = [
    ["01", "Validation placement changed failure containment."],
    ["02", "The effect depended strongly on model scale."],
    ["03", "No method demonstrated executable static plan fidelity."],
  ];
  for (let i = 0; i < items.length; i++) {
    const y = 214 + i * 112;
    text(s, items[i][0], 82, y, 54, 34, 18, C.mint, true);
    text(s, items[i][1], 152, y - 2, 900, 48, 27, C.paper, true);
    box(s, 152, y + 58, 850, 1, C.teal2);
  }
  text(s, "Final package: code, frozen raw evidence, processed tables, figures, manuscript, and reproducibility commands.", 82, 584, 1030, 50, 18, C.mint);
  text(s, "11", 1150, 670, 58, 20, 11, C.mint, true, "right");
}

const previewPaths = [];
for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1 });
  const previewPath = path.join(PREVIEW, `${stem}.png`);
  await fs.writeFile(previewPath, new Uint8Array(await png.arrayBuffer()));
  previewPaths.push(previewPath);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(PREVIEW, `${stem}.layout.json`), await layout.text());
}

const montageTiles = await Promise.all(previewPaths.map((previewPath, index) =>
  sharp(previewPath).resize(400, 225).toBuffer().then(input => ({
    input,
    left: (index % 3) * 400,
    top: Math.floor(index / 3) * 225,
  }))
));
await sharp({ create: { width: 1200, height: 900, channels: 3, background: "#D7DEDF" } })
  .composite(montageTiles)
  .webp({ quality: 88 })
  .toFile(path.join(OUT, "shepherd_ai_presentation_montage.webp"));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(path.join(OUT, "shepherd_ai_presentation.pptx"));
const inspect = await deck.inspect({ kind: "slide,textbox,shape,image", maxChars: 100000 });
await fs.writeFile(path.join(PREVIEW, "deck-inspect.ndjson"), inspect.ndjson);

export { deck };

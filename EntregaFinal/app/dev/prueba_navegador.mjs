import { chromium } from "playwright";
const csv = process.argv[2], out = process.argv[3];
const b = await chromium.launch();
for (const ancho of [1280, 390]) {
  const p = await b.newPage({ viewport: { width: ancho, height: 900 } });
  const errores = []; p.on("pageerror", e => errores.push(e.message));
  await p.goto("http://localhost:8000/");
  await p.setInputFiles("#archivo", csv);
  await p.waitForSelector("#pregunta:not([disabled])");
  await p.click("#sugerencias button");
  await p.waitForSelector(".respuesta:not(.cargando)", { timeout: 20000 });
  await p.click("details summary");
  await p.waitForTimeout(500);
  const desborde = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  const img = await p.evaluate(() => [...document.querySelectorAll(".paso img")].map(i => i.naturalWidth));
  console.log(ancho, "desborde:", desborde, "imgs:", img, "errores:", errores);
  await p.screenshot({ path: `${out}/web-${ancho}.png`, fullPage: true });
}
await b.close();

import { chromium } from "playwright";
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 390, height: 900 } });
let n = 0;
// Las 2 primeras consultas de estado reciben 429 y la tercera un 503, como haría API Gateway en un pico
await p.route("**/trabajos/**", (ruta) => (++n <= 3 ? ruta.fulfill({ status: n === 3 ? 503 : 429, body: '{"message":"Too Many Requests"}' }) : ruta.continue()));
await p.goto("http://localhost:8000/");
await p.setInputFiles("#archivo", process.argv[2]);
await p.waitForSelector("#pregunta:not([disabled])");
await p.click("#sugerencias button");
await p.waitForSelector(".respuesta:not(.cargando)", { timeout: 30000 });
const texto = await p.textContent(".mensaje:last-child .respuesta");
console.log("consultas:", n, "| respuesta:", texto.slice(0, 60));
console.log(texto.includes("Bogotá") ? "PASA" : "FALLA");
await b.close();

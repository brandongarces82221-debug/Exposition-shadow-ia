// Página del analista de datos: sube el CSV, envía preguntas y muestra los pasos del agente.
const API = (window.CONFIG && window.CONFIG.api ? window.CONFIG.api : "").replace(/\/$/, "");
const INTERVALO_MS = 1500;
const ESPERA_MAXIMA_MS = 5 * 60 * 1000;

const $ = (id) => document.getElementById(id);
const estado = { sesion: obtenerSesion(), conversacion: null, archivo: null, ocupado: false };

function nuevoId() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx".replace(/x/g, () => ((Math.random() * 16) | 0).toString(16));
}

function obtenerSesion() {
  let sesion = null;
  try { sesion = localStorage.getItem("sesion"); } catch (e) { /* almacenamiento bloqueado */ }
  if (!sesion) {
    sesion = nuevoId();
    try { localStorage.setItem("sesion", sesion); } catch (e) { /* se usa solo en memoria */ }
  }
  return sesion;
}

function escapar(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Markdown mínimo: negritas y saltos de línea (el texto se escapa antes)
function formatear(texto) {
  return escapar(texto).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
}

function agregarMensaje(clase, html) {
  const div = document.createElement("div");
  div.className = "mensaje " + clase;
  div.innerHTML = html;
  $("chat").appendChild(div);
  div.scrollIntoView({ behavior: "smooth", block: "end" });
  return div;
}

function habilitar(activo) {
  estado.ocupado = !activo;
  const listo = activo && !!estado.archivo;
  $("pregunta").disabled = !listo;
  $("enviar").disabled = !listo;
  $("sugerencias").hidden = !listo;
  $("pregunta").placeholder = estado.archivo ? "Escribe tu pregunta sobre el CSV" : "Sube un CSV para empezar";
}

async function pedir(ruta, opciones = {}) {
  const r = await fetch(API + ruta, opciones);
  let cuerpo = {};
  try { cuerpo = await r.json(); } catch (e) { /* respuesta sin JSON */ }
  return { codigo: r.status, cuerpo };
}

function mensajeDeError(codigo, cuerpo) {
  if (codigo === 429) return cuerpo.error || "Llegaste al límite de preguntas. Intenta más tarde.";
  if (codigo === 403) return "Esa conversación pertenece a otra sesión. Sube el CSV de nuevo para empezar.";
  return cuerpo.error || `Algo falló (código ${codigo}). Intenta de nuevo.`;
}

async function subirArchivo(archivo) {
  if (!archivo) return;
  if (archivo.size > 10 * 1024 * 1024) {
    $("estado-archivo").textContent = "El archivo pesa más de 10 MB; usa uno más pequeño.";
    return;
  }
  $("etiqueta-subir").classList.add("ocupado");
  $("estado-archivo").textContent = `Subiendo ${archivo.name}…`;
  try {
    const firma = await pedir("/archivos", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sesion: estado.sesion, nombre: archivo.name }),
    });
    if (firma.codigo !== 200) throw new Error(mensajeDeError(firma.codigo, firma.cuerpo));
    const datos = new FormData();
    Object.entries(firma.cuerpo.campos).forEach(([k, v]) => datos.append(k, v));
    datos.append("file", archivo);
    const subida = await fetch(firma.cuerpo.url, { method: "POST", body: datos });
    if (!subida.ok) throw new Error(`S3 rechazó el archivo (código ${subida.status}).`);

    estado.archivo = firma.cuerpo.archivo;
    estado.conversacion = nuevoId();
    $("chat").innerHTML = "";
    $("estado-archivo").innerHTML = `Archivo: <strong>${escapar(archivo.name)}</strong> · conversación nueva`;
    agregarMensaje("", "Listo. Pregúntame lo que quieras sobre este archivo.");
  } catch (e) {
    $("estado-archivo").textContent = e.message || "No se pudo subir el archivo.";
  } finally {
    $("etiqueta-subir").classList.remove("ocupado");
    $("archivo").value = "";
    habilitar(true);
  }
}

// Solo agrega los pasos nuevos, para no cerrar los bloques de código que el usuario abrió
function pintarPasos(contenedor, pasos) {
  const yaPintados = Number(contenedor.dataset.pintados || 0);
  contenedor.dataset.pintados = pasos.length;
  contenedor.insertAdjacentHTML("beforeend", pasos.slice(yaPintados).map((p) => {
    const imagenes = (p.imagenes || []).map((i) => `<img src="${escapar(i.url)}" alt="${escapar(i.nombre)}" loading="lazy">`).join("");
    if (p.tipo === "codigo") {
      return `<div class="paso"><details><summary>Código que ejecutó la IA</summary><pre>${escapar(p.codigo)}</pre></details></div>`;
    }
    if (p.tipo === "resultado") {
      const salida = p.texto ? `<details><summary>Resultado</summary><pre>${escapar(p.texto)}</pre></details>` : "";
      return `<div class="paso">${salida}${imagenes}</div>`;
    }
    if (p.tipo === "error") return `<div class="paso error">El código falló; la IA lo revisa:<pre>${escapar(p.texto)}</pre></div>`;
    if (p.tipo === "respuesta") return "";
    return `<div class="paso">${formatear(p.texto)}</div>`;
  }).join(""));
}

async function seguirTrabajo(trabajo, burbuja) {
  const pasos = burbuja.querySelector(".pasos");
  const final = burbuja.querySelector(".respuesta");
  const inicio = Date.now();
  while (Date.now() - inicio < ESPERA_MAXIMA_MS) {
    await new Promise((ok) => setTimeout(ok, INTERVALO_MS));
    let r;
    try {
      r = await pedir(`/trabajos/${encodeURIComponent(trabajo)}?sesion=${encodeURIComponent(estado.sesion)}`);
    } catch (e) {
      continue; // fallo de red momentáneo: se reintenta
    }
    if (r.codigo !== 200) {
      final.className = "respuesta paso error";
      final.textContent = mensajeDeError(r.codigo, r.cuerpo);
      return;
    }
    pintarPasos(pasos, r.cuerpo.pasos || []);
    if (r.cuerpo.estado === "listo" || r.cuerpo.estado === "error") {
      final.className = r.cuerpo.estado === "error" ? "respuesta paso error" : "respuesta";
      final.innerHTML = formatear(r.cuerpo.respuesta);
      return;
    }
  }
  final.className = "respuesta paso error";
  final.textContent = "La respuesta tardó demasiado. Intenta con una pregunta más concreta.";
}

async function preguntar(texto) {
  texto = texto.trim();
  if (!texto || estado.ocupado || !estado.archivo) return;
  habilitar(false);
  agregarMensaje("usuario", escapar(texto));
  $("pregunta").value = "";
  const burbuja = agregarMensaje("", '<div class="pasos"></div><div class="respuesta cargando">Analizando</div>');
  try {
    const r = await pedir("/preguntas", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sesion: estado.sesion, conversacion: estado.conversacion, archivo: estado.archivo, pregunta: texto }),
    });
    if (r.codigo !== 202) {
      const final = burbuja.querySelector(".respuesta");
      final.className = "respuesta paso error";
      final.textContent = mensajeDeError(r.codigo, r.cuerpo);
      return;
    }
    await seguirTrabajo(r.cuerpo.trabajo, burbuja);
  } catch (e) {
    const final = burbuja.querySelector(".respuesta");
    final.className = "respuesta paso error";
    final.textContent = "No hubo conexión con el servidor. Intenta de nuevo.";
  } finally {
    habilitar(true);
    $("pregunta").focus();
  }
}

$("archivo").addEventListener("change", (e) => subirArchivo(e.target.files[0]));
$("formulario").addEventListener("submit", (e) => { e.preventDefault(); preguntar($("pregunta").value); });
document.querySelectorAll("#sugerencias button").forEach((b) => b.addEventListener("click", () => preguntar(b.textContent)));
habilitar(true);

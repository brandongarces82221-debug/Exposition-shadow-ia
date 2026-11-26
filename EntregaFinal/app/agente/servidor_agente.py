"""Servidor del agente (puerto 8080). Lo llama API Gateway a través del VPC Link.

POST /preguntas {sesion, conversacion, archivo, pregunta} -> 202 {trabajo}  (el trabajo sigue en un hilo)
GET  /salud -> {ok: true}
"""

import json
import os
import re
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agente import responder
from almacen import Almacen

MAX_POR_DIA = 30
MAX_TURNOS = 20
MAX_PREGUNTA = 2000
ID = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


class ClienteSandbox:
    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def _post(self, ruta: str, datos: dict) -> dict:
        req = urllib.request.Request(self.url + ruta, data=json.dumps(datos).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"{}") | {"ok": False, "stdout": "",
                                                     "stderr": f"El sandbox respondió {e.code}", "imagenes": []}

    def resumen(self, sesion, archivo) -> str:
        r = self._post("/resumen", {"sesion": sesion, "archivo": archivo})
        if "resumen" not in r:
            raise RuntimeError(r.get("error") or "No se pudo leer el CSV")
        return r["resumen"]

    def ejecutar(self, sesion, trabajo, archivo, codigo) -> dict:
        return self._post("/ejecutar", {"sesion": sesion, "trabajo": trabajo, "archivo": archivo, "codigo": codigo})


def aceptar_pregunta(datos: dict, almacen: Almacen, lanzar):
    """Valida la pregunta, crea el trabajo y lo lanza. Devuelve (código HTTP, cuerpo)."""
    if not all(ID.fullmatch(str(datos.get(k, ""))) for k in ("sesion", "conversacion", "archivo")):
        return 400, {"error": "Faltan datos o tienen un formato inválido"}
    pregunta = str(datos.get("pregunta", "")).strip()
    if not pregunta or len(pregunta) > MAX_PREGUNTA:
        return 400, {"error": f"La pregunta debe tener entre 1 y {MAX_PREGUNTA} caracteres"}
    try:
        almacen.historial(datos["conversacion"], datos["sesion"])
    except PermissionError:
        return 403, {"error": "Esa conversación no es tuya"}
    if almacen.contar_hoy(datos["sesion"]) >= MAX_POR_DIA:
        return 429, {"error": f"Llegaste al límite de {MAX_POR_DIA} preguntas por día"}
    if almacen.contar_turnos(datos["conversacion"]) >= MAX_TURNOS:
        return 429, {"error": f"Esta conversación llegó a {MAX_TURNOS} preguntas; sube el CSV de nuevo para empezar otra"}
    trabajo = almacen.crear_trabajo(datos["sesion"], datos["conversacion"], datos["archivo"], pregunta)
    lanzar(trabajo)
    return 202, {"trabajo": trabajo}


def procesar_trabajo(trabajo, datos, almacen, modelo, sandbox, model_id="modelo"):
    sesion, archivo = datos["sesion"], datos["archivo"]
    try:
        historial = almacen.historial(datos["conversacion"], sesion)
        almacen.agregar_paso(trabajo, {"tipo": "pensando", "texto": "Leyendo el CSV…"})
        resumen = sandbox.resumen(sesion, archivo)
        r = responder(
            str(datos["pregunta"]).strip(), resumen, historial, modelo,
            lambda codigo: sandbox.ejecutar(sesion, trabajo, archivo, codigo),
            lambda paso: almacen.agregar_paso(trabajo, paso), model_id=model_id,
        )
        almacen.guardar_turno(datos["conversacion"], sesion, str(datos["pregunta"]).strip(),
                              r["codigos"], r["resumen_resultados"], r["respuesta"])
        almacen.terminar(trabajo, "listo", r["respuesta"])
    except Exception as e:
        print("ERROR en trabajo", trabajo, repr(e), flush=True)
        almacen.terminar(trabajo, "error", f"Algo falló al analizar: {type(e).__name__}. Intenta de nuevo.")


class Manejador(BaseHTTPRequestHandler):
    almacen = modelo = sandbox = None
    model_id = ""

    def _json(self, codigo: int, cuerpo: dict):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        self._json(200, {"ok": True}) if self.path == "/salud" else self._json(404, {"error": "no encontrado"})

    def do_POST(self):
        if self.path != "/preguntas":
            return self._json(404, {"error": "no encontrado"})
        try:
            largo = min(int(self.headers.get("Content-Length", 0)), 20_000)
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "JSON inválido"})
        cls = type(self)

        def lanzar(trabajo):
            threading.Thread(target=procesar_trabajo, daemon=True,
                             args=(trabajo, datos, cls.almacen, cls.modelo, cls.sandbox, cls.model_id)).start()

        self._json(*aceptar_pregunta(datos, cls.almacen, lanzar))

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    from anthropic import AnthropicBedrock

    Manejador.almacen = Almacen(os.environ["TABLA_TRABAJOS"], os.environ["TABLA_CONVERSACIONES"])
    Manejador.modelo = AnthropicBedrock(aws_region=os.environ.get("AWS_REGION", "us-east-1"))
    Manejador.sandbox = ClienteSandbox(os.environ["URL_SANDBOX"])
    Manejador.model_id = os.environ.get("MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
    puerto = int(os.environ.get("PUERTO", "8080"))
    print(f"Agente en puerto {puerto} | modelo={Manejador.model_id}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", puerto), Manejador).serve_forever()

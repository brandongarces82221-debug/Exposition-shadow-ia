"""Servidor interno del sandbox (puerto 8080). Solo lo llama el agente.

POST /ejecutar {sesion, trabajo, archivo, codigo} -> {ok, stdout, stderr, imagenes: [claves S3], segundos}
POST /resumen  {sesion, archivo}                  -> {resumen}
GET  /salud                                       -> {ok: true}
"""

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3

from ejecutor import ejecutar, leer_csv, resumen_csv

BUCKET = os.environ.get("BUCKET_DATOS", "")
PUERTO = int(os.environ.get("PUERTO", "8080"))
CUPOS = threading.BoundedSemaphore(4)  # máximo 4 ejecuciones a la vez por tarea
SEGMENTO = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def _segmento(valor) -> str:
    valor = str(valor or "")
    if not SEGMENTO.fullmatch(valor) or valor in (".", ".."):
        raise ValueError(f"identificador inválido: {valor!r}")
    return valor


def _leer_dataset(s3, bucket: str, datos: dict) -> bytes:
    clave = f"datasets/{_segmento(datos.get('sesion'))}/{_segmento(datos.get('archivo'))}"
    return s3.get_object(Bucket=bucket, Key=clave)["Body"].read()


def procesar_ejecucion(s3, bucket: str, datos: dict) -> dict:
    sesion, trabajo = _segmento(datos.get("sesion")), _segmento(datos.get("trabajo"))
    original = _leer_dataset(s3, bucket, datos)
    # Se entrega un CSV estándar (coma, UTF-8) aunque venga de Excel con ';' y latin-1
    normalizado = leer_csv(original).to_csv(index=False).encode("utf-8")
    with CUPOS:
        r = ejecutar(str(datos.get("codigo", "")), normalizado)
    claves = []
    for nombre, png in r["imagenes"]:
        clave = f"resultados/{sesion}/{trabajo}/{_segmento(nombre)}"
        s3.put_object(Bucket=bucket, Key=clave, Body=png, ContentType="image/png")
        claves.append(clave)
    return {**r, "imagenes": claves}


def procesar_resumen(s3, bucket: str, datos: dict) -> dict:
    return {"resumen": resumen_csv(_leer_dataset(s3, bucket, datos))}


class Manejador(BaseHTTPRequestHandler):
    s3 = None

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
        try:
            largo = min(int(self.headers.get("Content-Length", 0)), 200_000)
            datos = json.loads(self.rfile.read(largo) or b"{}")
            if self.path == "/ejecutar":
                self._json(200, procesar_ejecucion(self.s3, BUCKET, datos))
            elif self.path == "/resumen":
                self._json(200, procesar_resumen(self.s3, BUCKET, datos))
            else:
                self._json(404, {"error": "no encontrado"})
        except ValueError as e:
            self._json(400, {"error": str(e)})
        except Exception as e:  # el agente recibe el error y lo muestra como paso fallido
            print("ERROR:", repr(e), flush=True)
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    Manejador.s3 = boto3.client("s3")
    print(f"Sandbox en puerto {PUERTO}, bucket={BUCKET}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PUERTO), Manejador).serve_forever()

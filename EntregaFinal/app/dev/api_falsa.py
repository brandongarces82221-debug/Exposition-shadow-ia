"""API falsa para probar la página sin AWS.

Uso: python3 EntregaFinal/app/dev/api_falsa.py   y abrir http://localhost:8000
Sirve web/, imita /archivos, la subida a S3, /preguntas y /trabajos/{id} con pasos que aparecen poco a poco.
"""

import json
import re
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
trabajos = {}

PNG = None
try:
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(["Bogotá", "Medellín", "Cali", "Barranquilla", "Bucaramanga"], [412, 351, 290, 220, 160], color="#0E7C86")
    ax.set_title("Ventas por ciudad (ejemplo)")
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=110)
    PNG = buf.getvalue()
except ImportError:
    pass

PASOS = [
    (0.5, {"tipo": "pensando", "texto": "Leyendo el CSV…"}),
    (1.5, {"tipo": "codigo", "texto": "", "codigo": "import pandas as pd\ndf = pd.read_csv('entrada.csv')\nprint(df.groupby('ciudad')['unidades'].sum())"}),
    (2.5, {"tipo": "error", "texto": "KeyError: 'unidades '", "imagenes": []}),
    (3.0, {"tipo": "pensando", "texto": "El nombre de la columna tenía un espacio; lo corrijo."}),
    (4.0, {"tipo": "resultado", "texto": "ciudad\nBogotá      412\nMedellín    351\nCali        290",
           "imagenes": [{"nombre": "ventas.png", "url": "/img/ventas.png"}]}),
    (5.0, {"tipo": "respuesta", "texto": "**Bogotá** es la ciudad que más vende, con 412 unidades. Le siguen Medellín y Cali."}),
]


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def _json(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path == "/config.js":
            datos = b'window.CONFIG = { api: "" };'
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            return self.wfile.write(datos)
        if self.path == "/img/ventas.png" and PNG:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG)))
            self.end_headers()
            return self.wfile.write(PNG)
        m = re.match(r"^/trabajos/([\w-]+)", self.path)
        if m:
            t = trabajos.get(m.group(1))
            if not t:
                return self._json(404, {"error": "No existe"})
            transcurrido = time.time() - t
            pasos = [p for s, p in PASOS if s <= transcurrido]
            listo = transcurrido >= PASOS[-1][0]
            return self._json(200, {"estado": "listo" if listo else "en_curso", "pasos": pasos,
                                    "respuesta": PASOS[-1][1]["texto"] if listo else ""})
        return super().do_GET()

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(largo)
        if self.path == "/archivos":
            datos = json.loads(cuerpo or b"{}")
            archivo = "a1b2c3d4-" + re.sub(r"[^A-Za-z0-9._-]", "_", datos.get("nombre", "x.csv"))
            return self._json(200, {"url": "/subida", "campos": {"key": f"datasets/x/{archivo}"}, "archivo": archivo})
        if self.path == "/subida":
            self.send_response(204)
            return self.end_headers()
        if self.path == "/preguntas":
            trabajo = str(uuid.uuid4())
            trabajos[trabajo] = time.time()
            return self._json(202, {"trabajo": trabajo})
        self._json(404, {"error": "no encontrado"})


if __name__ == "__main__":
    print("API falsa en http://localhost:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), Manejador).serve_forever()

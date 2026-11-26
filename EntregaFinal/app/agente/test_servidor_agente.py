from conftest import ModeloFalso, texto

import servidor_agente as servidor
from almacen import Almacen

DATOS = {"sesion": "s1", "conversacion": "c1", "archivo": "v.csv", "pregunta": "¿total?"}


class SandboxFalso:
    def resumen(self, sesion, archivo):
        return "1 fila"

    def ejecutar(self, sesion, trabajo, archivo, codigo):
        return {"ok": True, "stdout": "1", "stderr": "", "imagenes": [], "segundos": 0.1}


def test_acepta_y_responde(tablas):
    a = Almacen("trabajos", "conversaciones")
    lanzados = []
    codigo, cuerpo = servidor.aceptar_pregunta(DATOS, a, lanzados.append)
    assert codigo == 202 and lanzados == [cuerpo["trabajo"]]
    servidor.procesar_trabajo(cuerpo["trabajo"], DATOS, a, ModeloFalso([[texto("Es 1.")]]), SandboxFalso())
    assert a.obtener(cuerpo["trabajo"])["estado"] == "listo"
    assert a.historial("c1", "s1")[0]["respuesta"] == "Es 1."


def test_error_de_bedrock_termina_en_error(tablas):
    a = Almacen("trabajos", "conversaciones")
    _, cuerpo = servidor.aceptar_pregunta(DATOS, a, lambda t: None)

    class ModeloRoto:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("Bedrock no disponible")

    servidor.procesar_trabajo(cuerpo["trabajo"], DATOS, a, ModeloRoto(), SandboxFalso())
    t = a.obtener(cuerpo["trabajo"])
    assert t["estado"] == "error" and t["respuesta"]


def test_cuota_agotada(tablas):
    a = Almacen("trabajos", "conversaciones")
    for _ in range(30):
        a.reservar_cuota("s1")
    assert servidor.aceptar_pregunta(DATOS, a, lambda t: None)[0] == 429


def test_conversacion_de_otra_sesion(tablas):
    a = Almacen("trabajos", "conversaciones")
    a.guardar_turno("c1", "otra", "p", [], "", "r")
    assert servidor.aceptar_pregunta(DATOS, a, lambda t: None)[0] == 403


def test_pregunta_vacia(tablas):
    a = Almacen("trabajos", "conversaciones")
    assert servidor.aceptar_pregunta({**DATOS, "pregunta": "  "}, a, lambda t: None)[0] == 400


def test_error_del_sandbox_conserva_el_detalle():
    # I1: si el sandbox responde 400/500, el modelo debe ver el motivo, no solo el código HTTP
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Falla(BaseHTTPRequestHandler):
        def do_POST(self):
            cuerpo = json.dumps({"error": "identificador inválido: 'x/y'"}).encode()
            self.send_response(400)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *a):
            pass

    http = HTTPServer(("127.0.0.1", 0), Falla)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    r = servidor.ClienteSandbox(f"http://127.0.0.1:{http.server_port}").ejecutar("s", "t", "a.csv", "print(1)")
    http.shutdown()
    assert r["ok"] is False and "identificador inválido" in r["stderr"]

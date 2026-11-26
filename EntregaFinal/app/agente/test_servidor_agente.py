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
        a.crear_trabajo("s1", "c9", "v.csv", "x")
    assert servidor.aceptar_pregunta(DATOS, a, lambda t: None)[0] == 429


def test_conversacion_de_otra_sesion(tablas):
    a = Almacen("trabajos", "conversaciones")
    a.guardar_turno("c1", "otra", "p", [], "", "r")
    assert servidor.aceptar_pregunta(DATOS, a, lambda t: None)[0] == 403


def test_pregunta_vacia(tablas):
    a = Almacen("trabajos", "conversaciones")
    assert servidor.aceptar_pregunta({**DATOS, "pregunta": "  "}, a, lambda t: None)[0] == 400

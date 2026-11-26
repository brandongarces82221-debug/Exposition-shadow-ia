from conftest import ModeloFalso, herramienta, texto

from agente import responder


def sandbox_ok(stdout="42"):
    llamadas = []

    def ejecutar(codigo):
        llamadas.append(codigo)
        return {"ok": True, "stdout": stdout, "stderr": "", "imagenes": ["resultados/s/t/g.png"], "segundos": 0.1}

    ejecutar.llamadas = llamadas
    return ejecutar


def test_responde_tras_una_herramienta():
    modelo = ModeloFalso([[texto("Voy a sumar."), herramienta("print(42)")], [texto("El total es 42.")]])
    pasos = []
    r = responder("¿Total?", "1 fila", [], modelo, sandbox_ok(), pasos.append)
    assert r["respuesta"] == "El total es 42."
    assert r["codigos"] == ["print(42)"]
    tipos = [p["tipo"] for p in pasos if p["tipo"] != "pensando"]
    assert tipos == ["codigo", "resultado", "respuesta"]


def test_responde_sin_herramienta():
    modelo = ModeloFalso([[texto("Hola, sube un CSV.")]])
    r = responder("hola", "1 fila", [], modelo, sandbox_ok(), lambda p: None)
    assert r["respuesta"] == "Hola, sube un CSV."
    assert r["codigos"] == []


def test_corta_en_6_iteraciones():
    sandbox = sandbox_ok()
    r = responder("bucle", "1 fila", [], ModeloFalso([], siempre_herramienta=True), sandbox, lambda p: None)
    assert len(sandbox.llamadas) == 6
    assert r["respuesta"].strip() != ""


def test_error_se_devuelve_al_modelo():
    modelo = ModeloFalso([[herramienta("1/0")], [texto("Corregido.")]])

    def falla(codigo):
        return {"ok": False, "stdout": "", "stderr": "ZeroDivisionError", "imagenes": [], "segundos": 0.1}

    responder("x", "1 fila", [], modelo, falla, lambda p: None)
    resultado = modelo.llamadas[1]["messages"][-1]["content"][0]
    assert resultado["type"] == "tool_result"
    assert resultado["is_error"] is True
    assert "ZeroDivisionError" in str(resultado["content"])


def test_historial_va_primero():
    historial = [
        {"pregunta": "¿Cuántas filas?", "codigos": ["print(len(df))"], "resumen_resultados": "10", "respuesta": "Hay 10."},
        {"pregunta": "¿Columnas?", "codigos": [], "resumen_resultados": "", "respuesta": "a y b."},
    ]
    modelo = ModeloFalso([[texto("ok")]])
    responder("¿Y ahora?", "1 fila", historial, modelo, sandbox_ok(), lambda p: None)
    mensajes = modelo.llamadas[0]["messages"]
    assert mensajes[0] == {"role": "user", "content": "¿Cuántas filas?"}
    assert mensajes[1]["role"] == "assistant" and "Hay 10." in mensajes[1]["content"]
    assert mensajes[-1] == {"role": "user", "content": "¿Y ahora?"}


def test_resumen_recortado():
    modelo = ModeloFalso([[herramienta("print('x'*5000)")], [texto("listo")]])
    r = responder("x", "1 fila", [], modelo, sandbox_ok("x" * 5000), lambda p: None)
    assert len(r["resumen_resultados"]) <= 1500

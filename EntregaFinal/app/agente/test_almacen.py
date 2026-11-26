import pytest

from almacen import Almacen


def test_trabajo_completo(tablas):
    a = Almacen("trabajos", "conversaciones")
    tid = a.crear_trabajo("s1", "c1", "v.csv", "¿total?")
    a.agregar_paso(tid, {"tipo": "codigo", "texto": "", "codigo": "print(1)"})
    a.terminar(tid, "listo", "Es 1.")
    t = a.obtener(tid)
    assert t["estado"] == "listo" and t["respuesta"] == "Es 1." and t["pasos"][0]["codigo"] == "print(1)"
    assert t["sesion"] == "s1"


def test_historial_ultimos_10(tablas):
    a = Almacen("trabajos", "conversaciones")
    for i in range(12):
        a.guardar_turno("c1", "s1", f"p{i}", [], "", f"r{i}")
    h = a.historial("c1", "s1")
    assert [t["pregunta"] for t in h] == [f"p{i}" for i in range(2, 12)]
    assert a.contar_turnos("c1") == 12


def test_historial_de_otra_sesion(tablas):
    a = Almacen("trabajos", "conversaciones")
    a.guardar_turno("c1", "s1", "p", [], "", "r")
    with pytest.raises(PermissionError):
        a.historial("c1", "otra")


def test_cuota_diaria(tablas):
    a = Almacen("trabajos", "conversaciones")
    assert a.contar_hoy("s1") == 0
    a.crear_trabajo("s1", "c1", "v.csv", "a")
    a.crear_trabajo("s1", "c1", "v.csv", "b")
    assert a.contar_hoy("s1") == 2

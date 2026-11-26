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
    a.reservar_cuota("s1")
    a.reservar_cuota("s1")
    assert a.contar_hoy("s1") == 2


def test_cuota_atomica_con_concurrencia(tablas):
    # I3: con la cuota en 29, de 20 pedidos simultáneos solo uno puede pasar
    from concurrent.futures import ThreadPoolExecutor
    a = Almacen("trabajos", "conversaciones")
    for _ in range(29):
        assert a.reservar_cuota("s1") is True
    with ThreadPoolExecutor(20) as ex:
        resultados = list(ex.map(lambda _: a.reservar_cuota("s1"), range(20)))
    assert resultados.count(True) == 1
    assert a.contar_hoy("s1") == 30


def test_cuota_global_diaria(tablas):
    # I3: cambiar de sesión no evita el tope global del día
    a = Almacen("trabajos", "conversaciones", maximo_global=3)
    assert [a.reservar_cuota(f"s{i}") for i in range(5)] == [True, True, True, False, False]

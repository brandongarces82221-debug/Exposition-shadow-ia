import os
import tempfile

from ejecutor import ejecutar, resumen_csv


def test_imprime_resultado():
    r = ejecutar("import pandas as pd; print(pd.read_csv('entrada.csv')['v'].sum())", b"v\n1\n2\n")
    assert r["ok"] is True
    assert "3" in r["stdout"]


def test_guarda_grafica():
    codigo = (
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1, 2])\n"
        "plt.savefig('salida/g.png')\n"
    )
    r = ejecutar(codigo, b"v\n1\n")
    assert r["ok"] is True
    assert r["imagenes"][0][0] == "g.png"
    assert r["imagenes"][0][1].startswith(b"\x89PNG")


def test_error_de_codigo():
    r = ejecutar("1/0", b"v\n1\n")
    assert r["ok"] is False
    assert "ZeroDivisionError" in r["stderr"]


def test_tiempo_maximo():
    r = ejecutar("while True: pass", b"v\n1\n", timeout=2)
    assert r["ok"] is False
    assert "tiempo" in r["stderr"].lower()
    assert r["segundos"] < 5


def test_salida_recortada():
    r = ejecutar("print('x' * 20000)", b"v\n1\n")
    assert len(r["stdout"]) <= 8000


def test_sin_credenciales(monkeypatch):
    monkeypatch.setenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/v2/credentials/secreto")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "no-debe-verse")
    r = ejecutar("import os; print(sorted(k for k in os.environ if 'AWS' in k))", b"v\n1\n")
    assert r["stdout"].strip() == "[]"


def test_resumen_csv_excel_colombia():
    texto = resumen_csv("ciudad;ventas\nBogotá;1,5\nCali;2\n".encode("latin-1"))
    assert "ciudad" in texto
    assert "ventas" in texto
    assert "Bogotá" in texto
    assert "2 columnas" in texto


def test_no_deja_archivos_temporales():
    tmp = tempfile.gettempdir()
    antes = set(os.listdir(tmp))
    ejecutar("print(1)", b"v\n1\n")
    despues = set(os.listdir(tmp))
    assert not any(n.startswith("ejecucion-") for n in despues - antes)


def test_salida_gigante_no_se_acumula():
    # C1: una salida sin fin debe cortarse a tiempo sin acumularse en memoria
    r = ejecutar("import sys\nwhile True: sys.stdout.write('x' * 10**6)", b"v\n1\n", timeout=3)
    assert r["ok"] is False
    assert len(r["stdout"]) <= 8000
    assert r["segundos"] < 6


def test_procesos_hijos_no_sobreviven(tmp_path):
    # C2: un proceso lanzado por el código no debe seguir vivo después de la ejecución
    marca = tmp_path / "sobrevivio.txt"
    codigo = (
        "import os, time\n"
        "if os.fork() == 0:\n"
        "    time.sleep(2)\n"
        f"    open({str(marca)!r}, 'w').write('si')\n"
        "    os._exit(0)\n"
        "print('padre listo')\n"
    )
    r = ejecutar(codigo, b"v\n1\n", timeout=10)
    assert r["ok"] is True and r["segundos"] < 5
    import time
    time.sleep(3)
    assert not marca.exists()


def test_csv_excel_con_miles_y_codigos():
    # I4: miles con punto, decimal con coma, y códigos con cero inicial que deben seguir siendo texto
    from ejecutor import leer_csv
    df = leer_csv("ciudad;ventas;codigo\nBogotá;1.234,5;05001\nCali;2.000;76001\n".encode("cp1252"))
    assert list(df["ventas"]) == [1234.5, 2000.0]
    assert list(df["codigo"]) == ["05001", "76001"]


def test_csv_punto_y_coma_con_punto_decimal():
    from ejecutor import leer_csv
    df = leer_csv(b"a;b\n1.5;x\n2;y\n")
    assert list(df["a"]) == [1.5, 2.0]


def test_csv_excel_cp1252():
    from ejecutor import leer_csv
    df = leer_csv("nombre;v\n“Ana”;1\n".encode("cp1252"))
    assert df["nombre"][0] == "“Ana”"

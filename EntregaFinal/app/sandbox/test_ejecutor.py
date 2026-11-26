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

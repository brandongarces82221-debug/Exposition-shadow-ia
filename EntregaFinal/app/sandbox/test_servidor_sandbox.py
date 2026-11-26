import boto3
import pytest
from moto import mock_aws

import servidor

BUCKET = "datos-prueba"


@pytest.fixture
def s3():
    with mock_aws():
        cliente = boto3.client("s3", region_name="us-east-1")
        cliente.create_bucket(Bucket=BUCKET)
        yield cliente


def test_ejecucion_sube_graficas(s3):
    s3.put_object(Bucket=BUCKET, Key="datasets/s1/v.csv", Body=b"v\n1\n2\n")
    codigo = "import matplotlib.pyplot as plt\nplt.plot([1,2])\nplt.savefig('salida/g.png')\nprint('listo')"
    r = servidor.procesar_ejecucion(s3, BUCKET, {"sesion": "s1", "trabajo": "t1", "archivo": "v.csv", "codigo": codigo})
    assert r["ok"] is True
    assert r["imagenes"] == ["resultados/s1/t1/g.png"]
    assert s3.get_object(Bucket=BUCKET, Key="resultados/s1/t1/g.png")["Body"].read().startswith(b"\x89PNG")


def test_csv_excel_se_normaliza(s3):
    s3.put_object(Bucket=BUCKET, Key="datasets/s1/e.csv", Body="ciudad;ventas\nBogotá;1,5\nCali;2\n".encode("latin-1"))
    codigo = "import pandas as pd; print(pd.read_csv('entrada.csv')['ventas'].sum())"
    r = servidor.procesar_ejecucion(s3, BUCKET, {"sesion": "s1", "trabajo": "t1", "archivo": "e.csv", "codigo": codigo})
    assert "3.5" in r["stdout"]


def test_resumen(s3):
    s3.put_object(Bucket=BUCKET, Key="datasets/s1/v.csv", Body=b"a,b\n1,2\n")
    assert "2 columnas" in servidor.procesar_resumen(s3, BUCKET, {"sesion": "s1", "archivo": "v.csv"})["resumen"]


def test_rechaza_rutas_raras(s3):
    with pytest.raises(ValueError):
        servidor.procesar_resumen(s3, BUCKET, {"sesion": "s1", "archivo": "../otra/v.csv"})


def test_grafica_con_tilde_y_espacios(s3):
    # I1: nombres como 'ventas_por_año.png' son normales en español y no deben romper la ejecución
    s3.put_object(Bucket=BUCKET, Key="datasets/s1/v.csv", Body=b"v\n1\n")
    codigo = "import matplotlib.pyplot as plt\nplt.plot([1])\nplt.savefig('salida/ventas por año.png')\nprint(42)"
    r = servidor.procesar_ejecucion(s3, BUCKET, {"sesion": "s1", "trabajo": "t1", "archivo": "v.csv", "codigo": codigo})
    assert r["ok"] is True and "42" in r["stdout"]
    assert r["imagenes"] == ["resultados/s1/t1/ventas_por_a_o.png"]


def test_rechaza_llamadas_desde_el_propio_contenedor():
    # C2 (agravante): el código del usuario no debe poder llamar al servidor por 127.0.0.1
    assert servidor.origen_permitido("10.20.0.15") is True
    assert servidor.origen_permitido("127.0.0.1") is False
    assert servidor.origen_permitido("::1") is False

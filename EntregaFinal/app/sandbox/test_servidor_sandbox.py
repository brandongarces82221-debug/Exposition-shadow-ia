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

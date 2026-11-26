import json
import os
import uuid

import boto3
import pytest
from moto import mock_aws

SESION = str(uuid.uuid4())


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("BUCKET_DATOS", "datos")
    monkeypatch.setenv("TABLA_TRABAJOS", "trabajos")
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="datos")
        boto3.client("dynamodb", region_name="us-east-1").create_table(
            TableName="trabajos", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "trabajo_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "trabajo_id", "AttributeType": "S"}])
        yield


def evento_post(cuerpo):
    return {"body": json.dumps(cuerpo), "isBase64Encoded": False}


def test_csv_devuelve_post_firmado(aws):
    import archivos
    r = archivos.handler(evento_post({"sesion": SESION, "nombre": "Ventas 2025.csv"}), None)
    assert r["statusCode"] == 200
    cuerpo = json.loads(r["body"])
    assert cuerpo["archivo"].endswith("Ventas_2025.csv")
    assert cuerpo["campos"]["key"] == f"datasets/{SESION}/{cuerpo['archivo']}"
    politica = json.loads(__import__("base64").b64decode(cuerpo["campos"]["policy"]))
    assert ["content-length-range", 1, 10485760] in politica["conditions"]


def test_rechaza_no_csv(aws):
    import archivos
    assert archivos.handler(evento_post({"sesion": SESION, "nombre": "virus.exe"}), None)["statusCode"] == 400


def test_rechaza_sesion_invalida(aws):
    import archivos
    assert archivos.handler(evento_post({"sesion": "../x", "nombre": "a.csv"}), None)["statusCode"] == 400


def _crear_trabajo(sesion, imagenes):
    boto3.resource("dynamodb", region_name="us-east-1").Table("trabajos").put_item(Item={
        "trabajo_id": "t1", "sesion": sesion, "estado": "listo", "respuesta": "Listo.",
        "pasos": [{"tipo": "resultado", "texto": "ok", "imagenes": imagenes}]})


def evento_get(trabajo, sesion):
    return {"pathParameters": {"id": trabajo}, "queryStringParameters": {"sesion": sesion}}


def test_trabajo_listo_con_imagen(aws):
    import trabajos
    _crear_trabajo(SESION, [f"resultados/{SESION}/t1/g.png"])
    r = trabajos.handler(evento_get("t1", SESION), None)
    cuerpo = json.loads(r["body"])
    assert r["statusCode"] == 200 and cuerpo["estado"] == "listo"
    url = cuerpo["pasos"][0]["imagenes"][0]["url"]
    assert "g.png" in url and ("X-Amz-Signature" in url or "Signature=" in url)


def test_trabajo_de_otra_sesion(aws):
    import trabajos
    _crear_trabajo("otra", [])
    assert trabajos.handler(evento_get("t1", SESION), None)["statusCode"] == 403


def test_trabajo_inexistente(aws):
    import trabajos
    assert trabajos.handler(evento_get("nada", SESION), None)["statusCode"] == 404


def test_no_firma_imagenes_de_otra_sesion(aws):
    import trabajos
    _crear_trabajo(SESION, ["resultados/otra/t9/robada.png"])
    cuerpo = json.loads(trabajos.handler(evento_get("t1", SESION), None)["body"])
    assert cuerpo["pasos"][0]["imagenes"] == []

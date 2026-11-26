"""POST /archivos {sesion, nombre} -> {url, campos, archivo}

Devuelve un POST firmado de S3 para que el navegador suba el CSV directo al bucket.
S3 rechaza archivos de más de 10 MB gracias a la condición content-length-range.
"""

import json
import os
import re
import uuid

import boto3

MAX_BYTES = 10 * 1024 * 1024
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
s3 = None


def _respuesta(codigo: int, cuerpo: dict) -> dict:
    return {"statusCode": codigo, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(cuerpo, ensure_ascii=False)}


def _sanear(nombre: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", nombre.strip())[-80:]
    return f"{uuid.uuid4().hex[:8]}-{base}"


def handler(event, context):
    global s3
    try:
        datos = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _respuesta(400, {"error": "JSON inválido"})
    sesion, nombre = str(datos.get("sesion", "")), str(datos.get("nombre", ""))
    if not UUID.fullmatch(sesion):
        return _respuesta(400, {"error": "Sesión inválida"})
    if not nombre.lower().endswith(".csv"):
        return _respuesta(400, {"error": "Solo se aceptan archivos .csv"})
    archivo = _sanear(nombre)
    s3 = s3 or boto3.client("s3")
    post = s3.generate_presigned_post(
        Bucket=os.environ["BUCKET_DATOS"], Key=f"datasets/{sesion}/{archivo}",
        Conditions=[["content-length-range", 1, MAX_BYTES]], ExpiresIn=300,
    )
    return _respuesta(200, {"url": post["url"], "campos": post["fields"], "archivo": archivo})

"""GET /trabajos/{id}?sesion=... -> {estado, pasos, respuesta}

Cada paso con gráficas trae sus imágenes como [{nombre, url}] con URLs firmadas de 10 minutos.
"""

import json
import os

import boto3

tabla = s3 = None


def _respuesta(codigo: int, cuerpo: dict) -> dict:
    return {"statusCode": codigo, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
            "body": json.dumps(cuerpo, ensure_ascii=False, default=str)}


def handler(event, context):
    global tabla, s3
    tabla = tabla or boto3.resource("dynamodb").Table(os.environ["TABLA_TRABAJOS"])
    s3 = s3 or boto3.client("s3")
    trabajo_id = (event.get("pathParameters") or {}).get("id", "")
    sesion = (event.get("queryStringParameters") or {}).get("sesion", "")
    if not trabajo_id or trabajo_id.startswith("cuota#"):
        return _respuesta(404, {"error": "No existe"})
    item = tabla.get_item(Key={"trabajo_id": trabajo_id}).get("Item")
    if not item:
        return _respuesta(404, {"error": "No existe"})
    if item.get("sesion") != sesion:
        return _respuesta(403, {"error": "Ese trabajo no es tuyo"})

    prefijo = f"resultados/{sesion}/"
    pasos = []
    for paso in item.get("pasos", []):
        imagenes = [
            {"nombre": clave.rsplit("/", 1)[-1],
             "url": s3.generate_presigned_url("get_object", ExpiresIn=600,
                                              Params={"Bucket": os.environ["BUCKET_DATOS"], "Key": clave})}
            for clave in paso.get("imagenes", []) if clave.startswith(prefijo)
        ]
        pasos.append({**paso, "imagenes": imagenes})
    return _respuesta(200, {"estado": item["estado"], "pasos": pasos, "respuesta": item.get("respuesta", "")})

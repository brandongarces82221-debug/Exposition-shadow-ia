"""Trabajos (pasos en vivo) y conversaciones (memoria) en DynamoDB."""

import time
import uuid
from datetime import datetime, timezone

import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

SIETE_DIAS = 7 * 24 * 3600
TURNOS_EN_MEMORIA = 10


class Almacen:
    def __init__(self, tabla_trabajos: str, tabla_conversaciones: str, maximo_global: int | None = None):
        # Tope de preguntas de todo el sistema por día: protege los créditos aunque alguien cambie de sesión
        self.maximo_global = maximo_global or int(os.environ.get("MAX_PREGUNTAS_GLOBAL_DIA", "300"))
        db = boto3.resource("dynamodb")
        self.trabajos = db.Table(tabla_trabajos)
        self.conversaciones = db.Table(tabla_conversaciones)

    @staticmethod
    def _expira() -> int:
        return int(time.time()) + SIETE_DIAS

    @staticmethod
    def _clave_cuota(sesion: str) -> str:
        return f"cuota#{sesion}#{datetime.now(timezone.utc):%Y-%m-%d}"

    def _sumar_si_cabe(self, clave: str, maximo: int) -> bool:
        """Suma 1 al contador solo si no ha llegado al máximo (atómico en DynamoDB)."""
        try:
            self.trabajos.update_item(
                Key={"trabajo_id": clave},
                UpdateExpression="ADD usadas :uno SET expira = :e",
                ConditionExpression="attribute_not_exists(usadas) OR usadas < :max",
                ExpressionAttributeValues={":uno": 1, ":e": self._expira(), ":max": maximo},
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def reservar_cuota(self, sesion: str, maximo: int = 30) -> bool:
        if not self._sumar_si_cabe(self._clave_cuota("global"), self.maximo_global):
            return False
        return self._sumar_si_cabe(self._clave_cuota(sesion), maximo)

    def crear_trabajo(self, sesion, conversacion, archivo, pregunta) -> str:
        trabajo_id = str(uuid.uuid4())
        self.trabajos.put_item(Item={
            "trabajo_id": trabajo_id, "sesion": sesion, "conversacion": conversacion, "archivo": archivo,
            "pregunta": pregunta, "estado": "en_curso", "pasos": [], "respuesta": "",
            "creado": int(time.time()), "expira": self._expira(),
        })
        return trabajo_id

    def obtener(self, trabajo_id: str):
        return self.trabajos.get_item(Key={"trabajo_id": trabajo_id}).get("Item")

    def agregar_paso(self, trabajo_id: str, paso: dict):
        self.trabajos.update_item(
            Key={"trabajo_id": trabajo_id},
            UpdateExpression="SET pasos = list_append(pasos, :p)",
            ExpressionAttributeValues={":p": [paso]},
        )

    def terminar(self, trabajo_id: str, estado: str, respuesta: str):
        self.trabajos.update_item(
            Key={"trabajo_id": trabajo_id},
            UpdateExpression="SET estado = :e, respuesta = :r",
            ExpressionAttributeValues={":e": estado, ":r": respuesta},
        )

    def contar_hoy(self, sesion: str) -> int:
        item = self.trabajos.get_item(Key={"trabajo_id": self._clave_cuota(sesion)}).get("Item") or {}
        return int(item.get("usadas", 0))

    def _turnos(self, conversacion: str) -> list:
        r = self.conversaciones.query(KeyConditionExpression=Key("conversacion").eq(conversacion))
        return r["Items"]

    def contar_turnos(self, conversacion: str) -> int:
        return len(self._turnos(conversacion))

    def historial(self, conversacion: str, sesion: str) -> list:
        turnos = self._turnos(conversacion)
        if any(t["sesion"] != sesion for t in turnos):
            raise PermissionError("La conversación pertenece a otra sesión")
        turnos.sort(key=lambda t: int(t["turno"]))
        return [
            {"pregunta": t["pregunta"], "codigos": list(t.get("codigos", [])),
             "resumen_resultados": t.get("resumen_resultados", ""), "respuesta": t["respuesta"]}
            for t in turnos[-TURNOS_EN_MEMORIA:]
        ]

    def guardar_turno(self, conversacion, sesion, pregunta, codigos, resumen, respuesta):
        self.conversaciones.put_item(Item={
            "conversacion": conversacion, "turno": self.contar_turnos(conversacion) + 1, "sesion": sesion,
            "pregunta": pregunta, "codigos": codigos, "resumen_resultados": resumen, "respuesta": respuesta,
            "expira": self._expira(),
        })

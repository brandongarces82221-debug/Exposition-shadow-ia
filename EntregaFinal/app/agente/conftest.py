from types import SimpleNamespace

import boto3
import pytest
from moto import mock_aws


def texto(t):
    return SimpleNamespace(type="text", text=t)


def herramienta(codigo, id_="h1"):
    return SimpleNamespace(type="tool_use", id=id_, name="ejecutar_python", input={"codigo": codigo})


class ModeloFalso:
    """Imita client.messages.create: devuelve respuestas preparadas en orden y guarda las llamadas."""

    def __init__(self, respuestas, siempre_herramienta=False):
        self.respuestas = list(respuestas)
        self.siempre_herramienta = siempre_herramienta
        self.llamadas = []
        self.messages = self

    def create(self, **kw):
        self.llamadas.append(kw)
        if kw.get("tool_choice", {}).get("type") == "none":
            return SimpleNamespace(stop_reason="end_turn", content=[texto("Resumen con lo que alcancé.")])
        if self.siempre_herramienta:
            return SimpleNamespace(stop_reason="tool_use", content=[herramienta("print(1)", f"h{len(self.llamadas)}")])
        bloques = self.respuestas.pop(0)
        usa = any(b.type == "tool_use" for b in bloques)
        return SimpleNamespace(stop_reason="tool_use" if usa else "end_turn", content=bloques)


@pytest.fixture
def tablas():
    with mock_aws():
        db = boto3.client("dynamodb", region_name="us-east-1")
        db.create_table(TableName="trabajos", BillingMode="PAY_PER_REQUEST",
                        KeySchema=[{"AttributeName": "trabajo_id", "KeyType": "HASH"}],
                        AttributeDefinitions=[{"AttributeName": "trabajo_id", "AttributeType": "S"}])
        db.create_table(TableName="conversaciones", BillingMode="PAY_PER_REQUEST",
                        KeySchema=[{"AttributeName": "conversacion", "KeyType": "HASH"},
                                   {"AttributeName": "turno", "KeyType": "RANGE"}],
                        AttributeDefinitions=[{"AttributeName": "conversacion", "AttributeType": "S"},
                                              {"AttributeName": "turno", "AttributeType": "N"}])
        yield

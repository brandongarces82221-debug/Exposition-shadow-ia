"""Genera datos-ejemplo/ventas.csv con ventas ficticias (semilla fija: siempre el mismo archivo)."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(2026)
ciudades = {"Bogotá": 1.4, "Medellín": 1.2, "Cali": 1.0, "Barranquilla": 0.8, "Bucaramanga": 0.6}
productos = {"Portátil": 3_200_000, "Monitor": 850_000, "Teclado": 120_000, "Mouse": 60_000, "Audífonos": 210_000}
destino = Path(__file__).resolve().parents[2] / "datos-ejemplo" / "ventas.csv"
with open(destino, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["fecha", "ciudad", "producto", "unidades", "precio_unitario"])
    dia = date(2025, 1, 3)
    for _ in range(200):
        dia += timedelta(days=random.randint(1, 3))
        ciudad = random.choices(list(ciudades), weights=list(ciudades.values()))[0]
        producto = random.choice(list(productos))
        temporada = 1.6 if dia.month in (11, 12) else 1.0
        unidades = max(1, int(random.gauss(4, 2) * ciudades[ciudad] * temporada))
        precio = int(productos[producto] * random.uniform(0.9, 1.1) / 1000) * 1000
        w.writerow([dia.isoformat(), ciudad, producto, unidades, precio])
print("Generado", destino)

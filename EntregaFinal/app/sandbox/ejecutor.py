"""Ejecuta código Python generado por la IA de forma aislada.

No usa red ni AWS: recibe el código y los bytes del CSV, y devuelve la salida y las gráficas.
El aislamiento de red lo da la subred privada; aquí se limita el proceso:
- subproceso con entorno vacío (sin credenciales del contenedor),
- tiempo máximo, límite de memoria y usuario sin privilegios (dentro del contenedor),
- directorio temporal propio que se borra al terminar.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pandas as pd

MAX_SALIDA = 8000
MEMORIA_MAX = 768 * 1024 * 1024
USUARIO_SIN_PRIVILEGIOS = "ejecutor"


def _recortar(texto: str) -> str:
    if len(texto) <= MAX_SALIDA:
        return texto
    aviso = "\n…[salida recortada]"
    return texto[: MAX_SALIDA - len(aviso)] + aviso


def _limitar_proceso():
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORIA_MAX, MEMORIA_MAX))
    except (ImportError, ValueError, OSError):
        pass  # macOS no siempre permite RLIMIT_AS; en el contenedor (Linux) sí aplica


def ejecutar(codigo: str, csv_bytes: bytes, timeout: int = 30) -> dict:
    directorio = tempfile.mkdtemp(prefix="ejecucion-")
    salida = os.path.join(directorio, "salida")
    os.makedirs(salida)
    with open(os.path.join(directorio, "entrada.csv"), "wb") as f:
        f.write(csv_bytes)

    extra = {}
    if hasattr(os, "getuid") and os.getuid() == 0:
        # Dentro del contenedor: el código corre como un usuario sin privilegios
        shutil.chown(directorio, USUARIO_SIN_PRIVILEGIOS)
        shutil.chown(salida, USUARIO_SIN_PRIVILEGIOS)
        extra["user"] = USUARIO_SIN_PRIVILEGIOS

    inicio = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", codigo],
            cwd=directorio,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "MPLBACKEND": "Agg", "HOME": directorio},
            capture_output=True,
            timeout=timeout,
            preexec_fn=_limitar_proceso,
            **extra,
        )
        ok = proc.returncode == 0
        stdout = proc.stdout.decode("utf-8", "replace")
        stderr = proc.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        ok = False
        stdout = (e.stdout or b"").decode("utf-8", "replace")
        stderr = f"Se superó el tiempo máximo de {timeout} s y la ejecución se detuvo."

    imagenes = []
    for nombre in sorted(os.listdir(salida)):
        if nombre.lower().endswith(".png"):
            with open(os.path.join(salida, nombre), "rb") as f:
                imagenes.append((nombre, f.read()))

    shutil.rmtree(directorio, ignore_errors=True)
    return {
        "ok": ok,
        "stdout": _recortar(stdout),
        "stderr": _recortar(stderr),
        "imagenes": imagenes[:5],
        "segundos": round(time.monotonic() - inicio, 2),
    }


def leer_csv(csv_bytes: bytes) -> pd.DataFrame:
    """Lee un CSV adivinando separador (, ; tab) y codificación (utf-8 o latin-1)."""
    for codificacion in ("utf-8", "latin-1"):
        try:
            texto = csv_bytes.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    primera = texto.splitlines()[0] if texto else ""
    sep = max([",", ";", "\t"], key=primera.count)
    decimal = "," if sep == ";" else "."
    return pd.read_csv(io.StringIO(texto), sep=sep, decimal=decimal)


def resumen_csv(csv_bytes: bytes) -> str:
    df = leer_csv(csv_bytes)
    tipos = "\n".join(f"- {c}: {t}" for c, t in df.dtypes.astype(str).items())
    return (
        f"{len(df)} filas y {len(df.columns)} columnas.\n"
        f"Columnas y tipos:\n{tipos}\n"
        f"Primeras filas:\n{df.head(5).to_string(index=False)}"
    )

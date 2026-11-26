"""Ejecuta código Python generado por la IA de forma aislada.

No usa red ni AWS: recibe el código y los bytes del CSV, y devuelve la salida y las gráficas.
El aislamiento de red lo da la subred privada; aquí se limita el proceso:
- subproceso con entorno vacío (sin credenciales del contenedor),
- tiempo máximo, límites de memoria, de tamaño de archivo y de procesos,
- salida a archivos con tope (nunca se acumula en la memoria del servidor),
- dentro del contenedor: un usuario sin privilegios por cupo, y al terminar se matan todos sus procesos,
- directorio temporal propio que se borra al terminar.
"""

import io
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import pandas as pd

MAX_SALIDA = 8000
MEMORIA_MAX = 768 * 1024 * 1024
ARCHIVO_MAX = 20 * 1024 * 1024  # ningún archivo escrito por el código puede pasar de 20 MB
PROCESOS_MAX = 64
USUARIO_POR_DEFECTO = "ejecutor1"


def _recortar(texto: str) -> str:
    if len(texto) <= MAX_SALIDA:
        return texto
    aviso = "\n…[salida recortada]"
    return texto[: MAX_SALIDA - len(aviso)] + aviso


def _leer_inicio(ruta: str) -> str:
    with open(ruta, "rb") as f:
        return f.read(MAX_SALIDA * 4).decode("utf-8", "replace")


def _es_root() -> bool:
    return hasattr(os, "getuid") and os.getuid() == 0


def _limites(con_usuario: bool):
    def aplicar():
        import resource

        for limite, valor in ((resource.RLIMIT_AS, MEMORIA_MAX), (resource.RLIMIT_FSIZE, ARCHIVO_MAX)):
            try:
                resource.setrlimit(limite, (valor, valor))
            except (ValueError, OSError):
                pass  # macOS no permite RLIMIT_AS; en el contenedor (Linux) sí aplica
        if con_usuario:
            # Solo con usuario propio: el límite cuenta todos los procesos de ese usuario
            resource.setrlimit(resource.RLIMIT_NPROC, (PROCESOS_MAX, PROCESOS_MAX))

    return aplicar


def _matar_restos(pgid: int, usuario):
    """Mata los procesos que el código dejó vivos (por grupo y, en el contenedor, por usuario)."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    if usuario:
        # Un hijo con el uid del cupo hace kill(-1): alcanza a todo lo de ese usuario, incluso con setsid
        import pwd

        info = pwd.getpwnam(usuario)
        pid = os.fork()
        if pid == 0:
            try:
                os.setgid(info.pw_gid)
                os.setuid(info.pw_uid)
                os.kill(-1, signal.SIGKILL)
            finally:
                os._exit(0)
        os.waitpid(pid, 0)


def ejecutar(codigo: str, csv_bytes: bytes, timeout: int = 30, usuario: str | None = None) -> dict:
    directorio = tempfile.mkdtemp(prefix="ejecucion-")
    salida = os.path.join(directorio, "salida")
    os.makedirs(salida)
    with open(os.path.join(directorio, "entrada.csv"), "wb") as f:
        f.write(csv_bytes)

    usuario = (usuario or USUARIO_POR_DEFECTO) if _es_root() else None
    extra = {}
    if usuario:
        os.chmod(directorio, 0o700)
        shutil.chown(directorio, usuario, usuario)
        shutil.chown(salida, usuario, usuario)
        extra = {"user": usuario, "group": usuario, "extra_groups": []}

    # La salida va a archivos fuera del directorio del código, así el código no puede reemplazarlos
    out = tempfile.NamedTemporaryFile(prefix="salida-", delete=False)
    err = tempfile.NamedTemporaryFile(prefix="error-", delete=False)
    inicio = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-c", codigo],
        cwd=directorio,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "MPLBACKEND": "Agg", "HOME": directorio},
        stdin=subprocess.DEVNULL, stdout=out, stderr=err,
        start_new_session=True,
        preexec_fn=_limites(bool(usuario)),
        **extra,
    )
    out.close()
    err.close()
    agotado = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        agotado = True
    _matar_restos(proc.pid, usuario)
    proc.wait()

    stdout = _leer_inicio(out.name)
    stderr = _leer_inicio(err.name)
    os.unlink(out.name)
    os.unlink(err.name)
    if agotado:
        stderr = f"Se superó el tiempo máximo de {timeout} s y la ejecución se detuvo."
    ok = not agotado and proc.returncode == 0

    imagenes = []
    for nombre in sorted(os.listdir(salida)):
        ruta = os.path.join(salida, nombre)
        if nombre.lower().endswith(".png") and os.path.isfile(ruta) and not os.path.islink(ruta):
            with open(ruta, "rb") as f:
                imagenes.append((nombre, f.read()))

    shutil.rmtree(directorio, ignore_errors=True)
    return {
        "ok": ok,
        "stdout": _recortar(stdout),
        "stderr": _recortar(stderr),
        "imagenes": imagenes[:5],
        "segundos": round(time.monotonic() - inicio, 2),
    }


# Números con formato colombiano (1.234,5) o internacional (1234.5)
EUROPEO = r"-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?"
SIMPLE = r"-?\d+(\.\d+)?"


def _a_numero(serie: pd.Series, sep: str) -> pd.Series:
    valores = serie.dropna().str.strip()
    if valores.empty or valores.str.match(r"-?0\d").any():
        return serie  # vacía, o códigos con cero inicial (DANE, NIT): se dejan como texto
    formatos = ["europeo", "simple"] if sep == ";" else ["simple"]
    for formato in formatos:
        if formato == "europeo" and valores.str.fullmatch(EUROPEO).all():
            limpio = serie.str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            return pd.to_numeric(limpio)
        if formato == "simple" and valores.str.fullmatch(SIMPLE).all():
            return pd.to_numeric(serie.str.strip())
    return serie


def leer_csv(csv_bytes: bytes) -> pd.DataFrame:
    """Lee un CSV adivinando separador (, ; tab), codificación (utf-8 o cp1252 de Excel) y formato de números."""
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = csv_bytes.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    primera = texto.splitlines()[0] if texto else ""
    sep = max([",", ";", "\t"], key=primera.count)
    df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=True)
    for columna in df.columns:
        df[columna] = _a_numero(df[columna], sep)
    return df


def resumen_csv(csv_bytes: bytes) -> str:
    df = leer_csv(csv_bytes)
    tipos = "\n".join(f"- {c}: {t}" for c, t in df.dtypes.astype(str).items())
    return (
        f"{len(df)} filas y {len(df.columns)} columnas.\n"
        f"Columnas y tipos:\n{tipos}\n"
        f"Primeras filas:\n{df.head(5).to_string(index=False)}"
    )

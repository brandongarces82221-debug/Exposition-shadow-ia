# Analista de datos con IA: plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** construir el código, la infraestructura (Terraform) y la estimación de costos del analista de datos con IA, listos para desplegar. **El ensayo en AWS (`terraform apply`) NO es parte de este plan** (decisión del usuario).

**Arquitectura:** página estática en S3 → API Gateway (HTTP API) → Lambdas (`archivos`, `trabajos`) y, por VPC Link + Cloud Map, el servicio ECS Fargate **agente**. El agente hace el ciclo de herramientas con Claude Haiku 4.5 en Bedrock y manda el código al servicio ECS **sandbox** (subred privada sin internet), que lee el CSV de S3 y guarda gráficas. Estado y memoria en DynamoDB.

**Tecnologías:** Python 3.12 (stdlib `http.server`, boto3, `anthropic[bedrock]>=1.17,<2`, pandas, matplotlib), pytest + moto para pruebas, HTML/JS sin framework, Terraform 1.17 con proveedores `hashicorp/aws ~> 6.0` y `kreuzwerker/docker ~> 3.0`.

**Diseño:** `EntregaFinal/docs/diseno-arquitectura.md` (leerlo antes de cada tarea).

## Restricciones globales

- Región `us-east-1`. Etiqueta `Proyecto=analista-datos` en todos los recursos (`default_tags`).
- Modelo `global.anthropic.claude-haiku-4-5-20251001-v1:0` vía `AnthropicBedrock(aws_region=...)`; sin `effort` ni `thinking`.
- Sin EC2, sin NAT, sin balanceador, sin EventBridge/Billing/Health, sin Route 53 DNS Firewall.
- Límites: CSV ≤ 10 MB (`content-length-range`), 6 iteraciones por pregunta, 30 s por ejecución, stdout/stderr recortados a 8 000 caracteres, resumen de resultado en historial ≤ 1 500 caracteres, historial = últimos 10 turnos, 30 preguntas por sesión al día, 20 turnos por conversación, 4 ejecuciones simultáneas por tarea de sandbox, TTL/ciclo de vida 7 días.
- Autoescalado 1–3 tareas por servicio (CPU 60 %). Fargate: agente 0,25 vCPU / 0,5 GB; sandbox 0,5 vCPU / 1 GB.
- Textos visibles y comentarios en español. Sin llaves de AWS en el código.
- Pruebas de Python se corren en el Codespace o en un venv local: `python3.12 -m venv .venv && .venv/bin/pip install -r EntregaFinal/app/requirements-dev.txt`.
- **No ejecutar `terraform apply`.** Verificación de Terraform = `fmt -check`, `validate` y `plan`.

## Foco de revisión

1. **CSV exportado de Excel en Colombia** (separador `;`, coma decimal, codificación latin-1): el resumen inicial debe leerlo bien en vez de mostrar una sola columna o fallar. → prueba en Tarea 1.
2. **Código que no termina** (`while True`) o que imprime muchísimo: debe cortarse a los 30 s y recortarse la salida, sin tumbar el sandbox. → prueba en Tarea 1.
3. **Una sesión pide una conversación o un archivo de otra sesión:** debe rechazarse (403), no filtrar datos. → pruebas en Tareas 2 y 3.
4. **El modelo responde sin usar la herramienta o se queda pidiéndola sin fin:** se acepta su respuesta; a las 6 iteraciones se cierra con lo que haya y estado `listo`. → prueba en Tarea 2.
5. **Error de Bedrock o del sandbox a mitad de la pregunta:** el trabajo queda en `error` con un mensaje legible, nunca colgado en `en_curso`. → prueba en Tarea 2.

---

## Estructura de archivos

```
EntregaFinal/
  README.md
  app/requirements-dev.txt          pytest, moto[s3,dynamodb], boto3, pandas, matplotlib, anthropic[bedrock]>=1.17,<2
  app/sandbox/ejecutor.py           ejecutar(codigo, csv_bytes) -> ResultadoEjecucion   (sin red, sin AWS)
  app/sandbox/servidor.py           HTTP: POST /ejecutar, POST /resumen, GET /salud   (S3 + ejecutor)
  app/sandbox/Dockerfile
  app/sandbox/test_ejecutor.py
  app/agente/almacen.py             Almacen: trabajos y conversaciones en DynamoDB
  app/agente/agente.py              responder(...) ciclo agéntico (modelo y sandbox inyectables)
  app/agente/servidor.py            HTTP: POST /preguntas (202), GET /salud
  app/agente/Dockerfile
  app/agente/test_agente.py, test_almacen.py
  app/lambdas/archivos.py, trabajos.py, test_lambdas.py
  web/index.html, web/app.js, web/estilos.css
  terraform/*.tf                    proveedores, red, datos, ecr, iam, ecs, api, lambdas, web, salidas
  costos/estimacion.md
  datos-ejemplo/ventas.csv
```

---

### Task 1 (Tarea 1): Sandbox (ejecutor + servidor + imagen)

**Archivos:** crear `app/sandbox/ejecutor.py`, `servidor.py`, `Dockerfile`, `test_ejecutor.py`, `app/requirements-dev.txt`.

**Interfaces producidas:**
- `ejecutar(codigo: str, csv_bytes: bytes, timeout: int = 30) -> dict` → `{"ok": bool, "stdout": str, "stderr": str, "imagenes": [(nombre: str, png: bytes)], "segundos": float}`.
- `resumen_csv(csv_bytes: bytes) -> str`: columnas, tipos, filas, primeras 5 filas; detecta separador (`,` `;` tab) y codificación (utf-8, si falla latin-1).
- HTTP (puerto 8080): `POST /ejecutar {sesion, trabajo, archivo, codigo}` → descarga `datasets/{sesion}/{archivo}`, ejecuta, sube PNG a `resultados/{sesion}/{trabajo}/{nombre}` y responde `{ok, stdout, stderr, imagenes: [claves S3], segundos}`; `POST /resumen {sesion, archivo}` → `{resumen}`; `GET /salud` → `{"ok": true}`. Variables: `BUCKET_DATOS`. Semáforo de 4 ejecuciones.

- [ ] **Paso 1: pruebas que fallan** en `test_ejecutor.py`:
  - `test_imprime_resultado`: `ejecutar("import pandas as pd; print(pd.read_csv('entrada.csv')['v'].sum())", b"v\n1\n2\n")` → `ok` y `"3"` en `stdout`.
  - `test_guarda_grafica`: código que hace `plt.plot([1,2]); plt.savefig('salida/g.png')` → `imagenes[0][0] == "g.png"` y bytes empiezan con `b"\x89PNG"`.
  - `test_error_de_codigo`: `"1/0"` → `ok is False` y `"ZeroDivisionError"` en `stderr`.
  - `test_tiempo_maximo`: `"while True: pass"` con `timeout=2` → `ok is False`, `"tiempo"` en `stderr.lower()`, `segundos < 5`.
  - `test_salida_recortada`: `"print('x'*20000)"` → `len(stdout) <= 8000`.
  - `test_sin_credenciales`: `"import os; print(sorted(k for k in os.environ if 'AWS' in k))"` con `AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` puesto en el proceso padre → `stdout.strip() == "[]"`.
  - `test_resumen_csv_excel_colombia`: `resumen_csv("ciudad;ventas\nBogotá;1,5\nCali;2\n".encode("latin-1"))` contiene `"ciudad"`, `"ventas"` y `"Bogotá"` (2 columnas, no 1).
- [ ] **Paso 2:** `pytest EntregaFinal/app/sandbox -v` → FALLA (módulo no existe).
- [ ] **Paso 3: implementar `ejecutor.py`:** directorio `tempfile.mkdtemp()` con `entrada.csv` y `salida/`; `subprocess.run([sys.executable, "-I", "-c", codigo], cwd=dir, env={"PATH": "/usr/bin:/bin", "MPLBACKEND": "Agg", "HOME": dir}, timeout=timeout, capture_output=True)`; en el contenedor el subproceso corre como usuario sin privilegios (`user=` cuando `os.getuid() == 0`) y con `resource.setrlimit(RLIMIT_AS, 768 MB)` en `preexec_fn`. Borrar el directorio al final.
- [ ] **Paso 4:** `pytest EntregaFinal/app/sandbox -v` → PASA.
- [ ] **Paso 5: `servidor.py` y `Dockerfile`** (`python:3.12-slim`, pandas, matplotlib, boto3; usuario `ejecutor` sin privilegios; `EXPOSE 8080`). Verificar: `docker build -t sandbox-local EntregaFinal/app/sandbox` termina OK y `docker run --rm -d -p 8080:8080 -e BUCKET_DATOS=x sandbox-local` + `curl localhost:8080/salud` → `{"ok": true}`.
- [ ] **Paso 6: commit** `"EntregaFinal: sandbox que ejecuta Python aislado"`.

### Task 2 (Tarea 2): Agente (almacén, ciclo agéntico, servidor, imagen)

**Archivos:** crear `app/agente/almacen.py`, `agente.py`, `servidor.py`, `Dockerfile`, `test_almacen.py`, `test_agente.py`.

**Interfaces consumidas:** HTTP del sandbox (Tarea 1).

**Interfaces producidas:**
- `Almacen(tabla_trabajos: str, tabla_conversaciones: str)` con: `crear_trabajo(sesion, conversacion, archivo, pregunta) -> str`, `agregar_paso(trabajo_id, paso: dict)`, `terminar(trabajo_id, estado: str, respuesta: str)`, `historial(conversacion, sesion) -> list[dict]` (últimos 10 turnos; `PermissionError` si la conversación es de otra sesión), `guardar_turno(conversacion, sesion, pregunta, codigos, resumen, respuesta)`, `contar_hoy(sesion) -> int`, `contar_turnos(conversacion) -> int`.
- `responder(pregunta: str, resumen_csv: str, historial: list, modelo, ejecutar_codigo, al_paso) -> dict` → `{"respuesta": str, "codigos": list[str], "resumen_resultados": str}`. `modelo` tiene `.messages.create(**kw)` (cliente de Anthropic o falso); `ejecutar_codigo(codigo) -> dict` (respuesta del sandbox); `al_paso(dict)` se llama en cada paso (`pensando`, `codigo`, `resultado`, `error`, `respuesta`).
- HTTP (puerto 8080): `POST /preguntas {sesion, conversacion, archivo, pregunta}` → `202 {trabajo}` (sigue en un hilo); `429` si `contar_hoy >= 30` o `contar_turnos >= 20`; `403` si la conversación es de otra sesión; `GET /salud`. Variables: `TABLA_TRABAJOS`, `TABLA_CONVERSACIONES`, `URL_SANDBOX`, `MODEL_ID`, `AWS_REGION`.
- Herramienta `ejecutar_python` con el texto exacto de la sección 5.3 del diseño; prompt del sistema según 5.3.

- [ ] **Paso 1: pruebas que fallan** (`test_agente.py` con un `ModeloFalso` que devuelve respuestas preparadas y un `ejecutar_codigo` falso):
  - `test_responde_tras_una_herramienta`: modelo pide `ejecutar_python` y luego responde texto → `respuesta` es ese texto, `codigos` tiene 1 elemento, `al_paso` recibió `codigo`, `resultado` y `respuesta` en ese orden.
  - `test_responde_sin_herramienta`: modelo responde texto directo → se acepta.
  - `test_corta_en_6_iteraciones`: modelo pide la herramienta siempre → se llama a `ejecutar_codigo` 6 veces y se devuelve una respuesta no vacía.
  - `test_error_se_devuelve_al_modelo`: el sandbox responde `ok: False` → el siguiente `messages.create` recibe un `tool_result` con `is_error: True`.
  - `test_historial_va_primero`: con historial de 2 turnos, los `messages` enviados empiezan con esos turnos.
  - `test_resumen_recortado`: un stdout de 5 000 caracteres deja `len(resumen_resultados) <= 1500`.
  - `test_error_de_bedrock_termina_en_error` (servidor con modelo que lanza excepción) → el trabajo queda `estado == "error"` con mensaje.
  - `test_almacen.py` con `moto`: `crear_trabajo` + `agregar_paso` + `terminar`; `historial` devuelve solo los últimos 10; `historial` de otra sesión lanza `PermissionError`.
- [ ] **Paso 2:** `pytest EntregaFinal/app/agente -v` → FALLA.
- [ ] **Paso 3: implementar** `almacen.py` (boto3 `resource("dynamodb")`; claves según 5.5 del diseño; contador diario como ítem `cuota#{sesion}#{fecha}` en la tabla de trabajos con `ADD`), `agente.py` (ciclo: `stop_reason == "tool_use"` → ejecutar cada `tool_use`, devolver todos los `tool_result` en un solo mensaje `user`; `max_tokens=4096`) y `servidor.py`.
- [ ] **Paso 4:** `pytest EntregaFinal/app/agente -v` → PASA.
- [ ] **Paso 5: `Dockerfile`** (`python:3.12-slim`, `anthropic[bedrock]>=1.17,<2`, boto3). Verificar `docker build` OK.
- [ ] **Paso 6: commit** `"EntregaFinal: agente con ciclo de herramientas y memoria"`.

### Task 3 (Tarea 3): Lambdas `archivos` y `trabajos`

**Archivos:** crear `app/lambdas/archivos.py`, `trabajos.py`, `test_lambdas.py`.

**Interfaces producidas** (formato de evento de HTTP API v2):
- `archivos.handler`: `POST /archivos {sesion, nombre}` → `200 {url, campos, archivo}` con `generate_presigned_post(Bucket, Key="datasets/{sesion}/{archivo}", Conditions=[["content-length-range", 1, 10485760]], ExpiresIn=300)`; `archivo` = nombre saneado (`[A-Za-z0-9._-]`, máx. 80) con prefijo aleatorio; `400` si no termina en `.csv` o `sesion` no es un UUID.
- `trabajos.handler`: `GET /trabajos/{id}?sesion=...` → `200 {estado, pasos, respuesta, imagenes: [{nombre, url}]}` con URLs firmadas de 10 min; `404` si no existe; `403` si el trabajo es de otra sesión.

- [ ] **Paso 1: pruebas que fallan** (`moto`): `test_csv_devuelve_post_firmado` (condición `content-length-range` presente con 10485760), `test_rechaza_no_csv` (400), `test_rechaza_sesion_invalida` (400), `test_trabajo_listo_con_imagen` (URL firmada presente), `test_trabajo_de_otra_sesion` (403), `test_trabajo_inexistente` (404).
- [ ] **Paso 2:** `pytest EntregaFinal/app/lambdas -v` → FALLA.
- [ ] **Paso 3:** implementar ambos `handler(event, context)`; variables `BUCKET_DATOS`, `TABLA_TRABAJOS`; respuestas con cabeceras CORS las pone API Gateway (no la Lambda).
- [ ] **Paso 4:** `pytest EntregaFinal/app/lambdas -v` → PASA.
- [ ] **Paso 5: commit** `"EntregaFinal: Lambdas de archivos y trabajos"`.

### Task 4 (Tarea 4): Página web y CSV de ejemplo

**Archivos:** crear `web/index.html`, `web/app.js`, `web/estilos.css`, `datos-ejemplo/ventas.csv`, `app/dev/api_falsa.py`.

**Interfaces consumidas:** las rutas de Tareas 2 y 3. La URL de la API llega en `web/config.js` (`window.CONFIG = {api: "..."}`), que genera Terraform (Tarea 5).

- [ ] **Paso 1:** `api_falsa.py` (stdlib, puerto 8000): sirve `web/`, responde a `/archivos` (acepta la subida en memoria), `/preguntas` y `/trabajos/{id}` con una secuencia fija de pasos (pensando → código → resultado con una gráfica de ejemplo → respuesta) para probar la interfaz sin AWS.
- [ ] **Paso 2: implementar la página:** sesión UUID en `localStorage` (con `try/catch`), botón "Subir CSV" (POST firmado como `FormData`), al subir abre conversación nueva y muestra el nombre; chat con preguntas sugeridas ("¿Qué mes vendió más?", "Gráfica de ventas por ciudad", "Ahora solo 2025"); consulta `GET /trabajos/{id}` cada 1,5 s; muestra cada paso (el código en un bloque plegable, errores en rojo, gráficas como `<img>`); mensajes claros para `429` y `403`. Funciona a ancho de celular.
- [ ] **Paso 3: `ventas.csv`:** ~200 filas ficticias con `fecha, ciudad, producto, unidades, precio_unitario`, 2025–2026, 5 ciudades de Colombia.
- [ ] **Paso 4: verificar** con `python3 EntregaFinal/app/dev/api_falsa.py` y captura de Chrome sin interfaz gráfica a 1280 px y 390 px: se ven los pasos, el código plegable y la gráfica; sin desborde horizontal.
- [ ] **Paso 5: commit** `"EntregaFinal: página del chat y datos de ejemplo"`.

### Task 5 (Tarea 5): Terraform

**Archivos:** crear `terraform/proveedores.tf`, `variables.tf`, `red.tf`, `datos.tf`, `ecr.tf`, `iam.tf`, `ecs.tf`, `api.tf`, `lambdas.tf`, `web.tf`, `salidas.tf`.

**Interfaces consumidas:** Dockerfiles (Tareas 1 y 2), `app/lambdas/*.py` (Tarea 3), `web/` (Tarea 4).

Contenido fijado por el diseño (el resto lo decide el implementador):
- **red:** VPC `10.20.0.0/16`, 2 zonas (`us-east-1a`, `us-east-1b`), 2 subredes públicas con IGW, 2 privadas sin ruta a internet; endpoint gateway S3 con **política** que solo permite `arn:aws:s3:::{bucket_datos}/*` y `arn:aws:s3:::prod-us-east-1-starport-layer-bucket/*`, asociado a las tablas privadas; endpoints de interfaz `ecr.api`, `ecr.dkr`, `logs` en **una** subred privada con DNS privado; grupos de seguridad: agente (entrada 8080 solo desde el SG del VPC Link; salida 443 a todo y 8080 al SG del sandbox), sandbox (entrada 8080 solo desde el SG del agente; salida solo 443 al SG de endpoints y al prefix list de S3), VPC Link, endpoints (443 desde el sandbox).
- **datos:** bucket web (sitio estático, lectura pública), bucket de datos privado (cifrado, regla de ciclo de vida 7 días, CORS para POST desde el sitio), tablas `trabajos` (PK `trabajo_id`) y `conversaciones` (PK `conversacion`, SK `turno` N), ambas on-demand con TTL `expira`.
- **ecr + imágenes:** 2 repositorios; `docker_image` + `docker_registry_image` (proveedor `kreuzwerker/docker`, autenticación con `aws_ecr_authorization_token`), con `triggers` = hash de los archivos de cada app.
- **iam:** roles de ejecución de tareas (pull ECR + logs); rol de tarea agente (`bedrock:InvokeModel` sobre `arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0` y `arn:aws:bedrock:us-east-1:{cuenta}:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0`, y CRUD en las 2 tablas); rol de tarea sandbox (`s3:GetObject datasets/*`, `s3:PutObject resultados/*`); roles de Lambda (presign/lectura y `GetItem`).
- **ecs:** clúster; namespace privado de Cloud Map; servicio agente en subredes públicas con IP pública, registro **SRV**; servicio sandbox en subredes privadas sin IP pública, registro A (`sandbox.analista.local`); `readonlyRootFilesystem = true` en el sandbox con volumen de `/tmp`; autoescalado (Application Auto Scaling, CPU 60 %, 1–3); logs a CloudWatch con retención de 7 días.
- **api:** HTTP API con CORS para el origen del sitio; rutas `POST /archivos`, `GET /trabajos/{id}` (Lambda) y `POST /preguntas` (VPC Link → servicio Cloud Map del agente); throttling por defecto 10 req/s, ráfaga 20.
- **web:** `aws_s3_object` por archivo de `web/` con `content_type` y `config.js` generado con la URL de la API.
- **salidas:** `url_web`, `url_api`.

- [ ] **Paso 1:** escribir los archivos.
- [ ] **Paso 2: verificar** en el Codespace (`EntregaFinal/terraform`): `terraform fmt -check` sin salida, `terraform init` y `terraform validate` → "Success!", `terraform plan` sin errores (sin `apply`). Anotar el número de recursos del plan en el README.
- [ ] **Paso 3: commit** `"EntregaFinal: infraestructura en Terraform"`.

### Task 6 (Tarea 6): Costos y README

**Archivos:** crear `costos/estimacion.md`, `EntregaFinal/README.md`; actualizar el README de la raíz (fila de `EntregaFinal/`).

- [ ] **Paso 1: `estimacion.md`:** tabla de la sección 6 del diseño con los precios de us-east-1 verificados en las páginas oficiales de precios de AWS (Fargate, VPC endpoints, IPv4 pública, Bedrock Haiku 4.5, Lambda, API Gateway, DynamoDB, S3) y la fecha de consulta; dos escenarios ("24/7" y "solo demo, 10 h"); **la lista exacta de lo que hay que cargar en https://calculator.aws** (servicio, región, cantidad y configuración de cada línea) para que el usuario arme la estimación y guarde el enlace compartible; un espacio para pegar ese enlace.
- [ ] **Paso 2: `README.md` de EntregaFinal:** qué es, la imagen `arquitectura/arquitectura-general.png`, requisitos, cómo probar localmente (`api_falsa.py` y `pytest`), cómo levantar (`terraform init && terraform apply`) y apagar (`terraform destroy`), qué hacer si el Codespace se borra (buscar recursos por la etiqueta `Proyecto=analista-datos`), costo por hora.
- [ ] **Paso 3: verificar** que todos los enlaces relativos del README existen (`ls` de cada ruta).
- [ ] **Paso 4: commit y push** `"EntregaFinal: estimación de costos y README"`.

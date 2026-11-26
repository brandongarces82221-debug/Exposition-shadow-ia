# Diseño: Analista de datos con IA en AWS

Proyecto final de Computación en la Nube. Fecha del diseño: 2026-11-26.

## 1. Qué es y por qué

Una aplicación web donde una persona **sube un CSV** (ventas, notas, gastos…) y **le pregunta en lenguaje natural**:
"¿qué mes vendimos más?", "hazme una gráfica de ventas por ciudad". Un **agente** con Claude en Amazon Bedrock
decide qué hacer, **escribe código Python, lo ejecuta en un contenedor aislado**, lee el resultado, corrige si hubo error
y responde con texto y gráficas.

Por qué este proyecto:
- La clase enseñó **agentes**: aquí el agente piensa, usa una herramienta, observa y se corrige (ciclo agéntico real).
- Cada servicio de AWS tiene un papel justificable en la presentación.
- La entrega exige tres cosas: **diagrama en draw.io**, **costo con la AWS Pricing Calculator** y **despliegue con Terraform**.

**Éxito se ve así:** en la demo, alguien sube un CSV desconocido, hace una pregunta y el curso ve los pasos en vivo
("escribiendo código… ejecutando… error, corrigiendo… listo") hasta una respuesta con gráfica, en menos de un minuto.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
- **Proyecto "real":** varias personas a la vez (p. ej. todo el curso desde el celular), cada una con su sesión y sus archivos.
- **Conversación con memoria:** se puede seguir preguntando sobre la respuesta anterior ("ahora hazla por mes").
- Chat sobre un CSV subido, con respuestas en texto y gráficas (PNG).
- Pasos del agente visibles en vivo en la página.
- El código generado por la IA corre **aislado**: sin internet y sin acceso a otros recursos de la cuenta.
- Todo se crea con `terraform apply` y se borra con `terraform destroy`.
- Diagrama draw.io y estimación de costos coherentes con lo que Terraform crea.

**No objetivos**
- Inicio de sesión de usuarios (Cognito). La sesión es un identificador aleatorio en el navegador.
- Alta disponibilidad multirregión. (Sí hay: tareas repartidas en 2 zonas y autoescalado de 1 a 3 tareas por servicio.)
- Archivos distintos de CSV (Excel, bases de datos).
- Dominio propio, HTTPS propio o CDN.

**Anti-objetivos** (aunque funcione, sería un fracaso si…)
- El código de la IA puede salir a internet (HTTP/HTTPS) o leer credenciales/recursos de la cuenta.
- Mantenerlo levantado gasta los créditos sin darse cuenta (debe quedar claro el costo por hora y cómo apagarlo).
- Un servicio del diagrama no tiene un papel real ("puesto por poner").
- La demo depende de pasos manuales en la consola de AWS.

## 3. Restricciones

- Cuenta AWS con **pocos créditos**: se levanta para ensayar y para la demo, y se destruye.
- Región **us-east-1**.
- Modelo: **Claude Haiku 4.5** en Bedrock, perfil de inferencia `global.anthropic.claude-haiku-4-5-20251001-v1:0`
  (es el único modelo habilitado en la cuenta; verificado en la exposición anterior).
- SDK `anthropic[bedrock]>=1.17,<2` con el cliente `AnthropicBedrock` (la 2.x usa una versión de API que Bedrock
  solo acepta para modelos 4.7+). Haiku 4.5 no usa `effort`; el uso de herramientas (tool use) sí está soportado.
- Servicios elegidos: S3, API Gateway, Lambda, ECR, ECS (Fargate), Bedrock, DynamoDB, VPC, IAM y CloudWatch (solo logs).
  **Sin EC2** (decisión del usuario: Fargate administra las máquinas). Sin EventBridge, Billing ni Health.
- Despliegue desde el GitHub Codespace del usuario (verificado: Terraform 1.17, AWS CLI y Docker 29 disponibles).
- Cuenta AWS normal (no es AWS Academy ni pertenece a una Organization; sin bloqueo de acceso público de S3 a nivel de cuenta). Se pueden crear roles IAM propios.
- Todo el proyecto vive en `EntregaFinal/` dentro del repo `Exposition-shadow-ia`.

## 4. Enfoques considerados

| Enfoque | Cómo | A favor | En contra |
|---|---|---|---|
| **1. Agente y sandbox como servicios en ECS** ✅ elegido | Dos servicios Fargate siempre encendidos durante la demo: agente (habla con Bedrock) y sandbox (ejecuta Python, subred sin internet). Lambda para lo liviano. | Rápido (sin arranques en frío por paso), aislamiento claro, cada servicio con papel real. | Cobra por hora mientras está encendido. |
| 2. Todo bajo demanda | Agente en Lambda; cada ejecución lanza una tarea Fargate (RunTask). | ~US$0 en reposo. | 30–60 s de arranque por paso: una pregunta de 3 pasos tarda minutos. Mala demo. |
| 3. Un EC2 con Docker | Todo en una máquina. | Lo más simple y barato. | ECS/ECR casi decorativos, aislamiento débil, luce menos para la materia. |

El usuario eligió el **enfoque 1**. Alternativa anotada: si el profesor exige EC2, ECS puede correr sobre una
instancia EC2 (capacity provider) en vez de Fargate, sin cambiar el resto.

## 5. Arquitectura

```
                         Navegador (página en S3, sitio web estático)
                                     │ HTTPS
                                     ▼
                           API Gateway (HTTP API)
             ┌───────────────────────┼─────────────────────────┐
   POST /archivos            POST /preguntas          GET /trabajos/{id}
             │                       │ (VPC Link)               │
             ▼                       ▼                          ▼
      Lambda "archivos"     ┌──── VPC 10.20.0.0/16 ─────────────────────────────┐   Lambda "trabajos"
      (URL firmada para     │ Subred pública                                    │   (lee DynamoDB)
       subir el CSV a S3)   │   ECS Fargate: AGENTE ──► Amazon Bedrock          │
                            │        │  (Claude Haiku 4.5, tool use)            │
                            │        │ HTTP interno (Cloud Map)                 │
                            │ Subred privada (SIN internet)                     │
                            │   ECS Fargate: SANDBOX (ejecuta Python)           │
                            │        │                                          │
                            │   Endpoints de VPC: S3 (gateway), ECR, Logs       │
                            └────────┼──────────────────────────────────────────┘
                                     ▼
                     S3 (datasets/ y resultados/)        DynamoDB (trabajos)
                     ECR (imágenes agente y sandbox)     CloudWatch Logs
```

### 5.1 Piezas y su papel

| Pieza | Papel |
|---|---|
| **S3 – bucket web** | Sitio estático (HTML/JS) con el chat. Público solo para lectura. |
| **S3 – bucket de datos** | `datasets/{sesion}/{archivo}.csv` (subidos) y `resultados/{sesion}/{trabajo}/*.png` (gráficas). Privado. Regla de ciclo de vida: borrar a los 7 días. |
| **API Gateway (HTTP API)** | Única puerta de entrada. CORS para el sitio. Limitación de tasa (throttling) para cuidar créditos. |
| **Lambda `archivos`** | Valida el nombre (solo `.csv`) y devuelve un **POST firmado** de S3 con la condición `content-length-range` 1 B–10 MB, para que S3 rechace archivos más grandes aunque el navegador mienta. |
| **Lambda `trabajos`** | Devuelve el estado de un trabajo desde DynamoDB y URLs firmadas de las gráficas. |
| **VPC Link + Cloud Map** | Conecta API Gateway con el servicio del agente dentro de la VPC sin balanceador (ahorra ~US$16/mes). El servicio ECS del agente se registra con registros **SRV** (API Gateway necesita el puerto). Cloud Map también da el nombre interno del sandbox. |
| **ECS Fargate – agente** | Servicio con **autoescalado de 1 a 3 tareas** (por CPU) en 2 zonas; no guarda estado en memoria: todo va a DynamoDB, así cualquier tarea puede atender cualquier pregunta. Recibe la pregunta, crea el trabajo en DynamoDB, responde `202` con el id y sigue trabajando en segundo plano: ciclo agéntico con Bedrock, llama al sandbox, guarda cada paso en DynamoDB. Subred pública con IP pública para llegar a Bedrock (sin NAT, que costaría ~US$32/mes). Su grupo de seguridad solo acepta tráfico del VPC Link. |
| **ECS Fargate – sandbox** | Servicio con **autoescalado de 1 a 3 tareas** (por CPU); cada tarea ejecuta hasta 4 códigos a la vez. Servidor interno que recibe `{sesion, trabajo, codigo}`, descarga el CSV de la sesión, ejecuta el código con límites y sube las gráficas. **Subred privada sin ruta a internet.** Solo acepta tráfico del agente. |
| **Endpoints de VPC** | S3 (gateway, gratis) para el sandbox, con **política de endpoint** que solo permite el bucket de datos y el bucket de capas de ECR (`prod-us-east-1-starport-layer-bucket`); ECR (`ecr.api`, `ecr.dkr`) y CloudWatch Logs (interface) para que el sandbox pueda arrancar y escribir logs sin internet. En **una sola zona** para ahorrar. |
| **ECR** | Dos repositorios: `analista-agente` y `analista-sandbox`. |
| **Bedrock** | Claude Haiku 4.5 con herramientas. |
| **DynamoDB** | Tabla `trabajos` (on-demand). TTL de 7 días. |
| **IAM** | Un rol por pieza con permisos mínimos (ver 5.4). |
| **CloudWatch** | Logs de las Lambdas y de ECS (retención 7 días) y las métricas de CPU que disparan el autoescalado de ECS. |

### 5.2 Flujo de una pregunta

1. La página crea un `sesion` aleatorio (guardado en `localStorage`). Cada CSV abre una **conversación** (`conversacion`).
2. Subir CSV: `POST /archivos` → Lambda devuelve URL firmada → el navegador sube a `datasets/{sesion}/…`.
3. Preguntar: `POST /preguntas {sesion, conversacion, archivo, pregunta}` → el agente responde `202 {trabajo}`.
4. El agente (en segundo plano):
   1. Lee las primeras filas y columnas del CSV pidiéndoselo al sandbox (primer paso automático, para dar contexto).
   2. Carga el **historial** de la conversación (últimos 10 turnos) desde DynamoDB y llama a Bedrock con el historial,
      la pregunta nueva, el resumen del CSV y la herramienta `ejecutar_python`.
   3. Si el modelo pide la herramienta, envía el código al sandbox, recibe `stdout`, `stderr` y gráficas, y se lo devuelve al modelo.
   4. Repite hasta que el modelo responda sin pedir herramientas, o hasta **6 iteraciones** (después responde con lo que tenga).
   5. Cada paso se guarda en DynamoDB: `pensando`, `codigo`, `resultado`, `error`, `respuesta`.
   6. Al terminar, guarda el turno en el historial: la pregunta, el código ejecutado, un **resumen corto** de cada
      resultado (máx. 1 500 caracteres) y la respuesta. Así el historial no crece sin control.
5. La página consulta `GET /trabajos/{id}` cada 1–2 s y muestra los pasos (código incluido, plegable) hasta `estado = listo`.

### 5.3 Herramienta del agente

`ejecutar_python(codigo: str)`: "Ejecuta Python 3.12 con pandas y matplotlib. El CSV está en `entrada.csv` (directorio actual).
Guarda gráficas con `plt.savefig('salida/nombre.png')`. Imprime con `print` lo que necesites ver."

Cada ejecución corre en **su propio directorio temporal** (`/tmp/ejecuciones/{uuid}/` con `entrada.csv` y `salida/`), así
que varias preguntas simultáneas no se pisan. El sandbox atiende hasta 4 ejecuciones a la vez; las demás esperan.

Respuesta del sandbox: `{ok, stdout (recortado a 8 000 caracteres), stderr (recortado), imagenes: [claves S3], segundos}`.

Prompt del sistema del agente (idea): analista de datos que responde en español, siempre verifica con código antes de
afirmar un número, prefiere una gráfica cuando ayuda, y explica el resultado en 2–4 frases.

### 5.4 Seguridad del sandbox (el punto crítico)

El código lo escribe la IA y puede venir influido por el contenido del CSV (inyección indirecta, como en la exposición
anterior). Capas:
1. **Red:** subred privada sin NAT ni IGW; grupo de seguridad sin salida excepto a los endpoints de VPC. No hay salida
   HTTP/HTTPS a internet.
2. **Permisos IAM del sandbox:** solo `s3:GetObject` en `datasets/*` y `s3:PutObject` en `resultados/*`.
3. **Proceso:** el servidor del sandbox descarga el CSV **él mismo** y ejecuta el código en un subproceso con usuario sin
   privilegios, **variables de entorno vacías** (sin la URI de credenciales del contenedor), tiempo máximo 30 s,
   límite de memoria y directorio de trabajo temporal que se borra al final.
4. **Contenedor:** sistema de archivos de solo lectura salvo `/tmp`; sin privilegios.
5. **Endpoint de S3 con política:** aunque el código intente subir datos a un bucket ajeno de forma anónima, el endpoint solo deja pasar el bucket de datos y el de capas de ECR.

Riesgos residuales (se dicen en la presentación, como parte del análisis crítico):
- **Fuga por DNS:** el resolvedor DNS de la VPC sigue respondiendo nombres públicos, y un código malicioso podría
  codificar datos en consultas DNS hacia un dominio del atacante. Cerrarlo exige Route 53 DNS Firewall; **el usuario
  decidió no agregarlo** (no es parte de lo visto en clase). Queda documentado como riesgo conocido y su solución.
- Un código malicioso podría intentar adivinar la ruta de credenciales del contenedor; por eso el rol del sandbox es
  mínimo.

### 5.5 Datos en DynamoDB

Tabla `trabajos`, clave `trabajo_id` (string). Atributos: `sesion`, `conversacion`, `archivo`, `pregunta`, `estado`
(`en_curso | listo | error`), `pasos` (lista de `{tipo, texto, codigo?, imagenes?}`), `respuesta`, `creado`, `expira` (TTL).

Tabla `conversaciones` (historial para la memoria), clave de partición `conversacion` y de orden `turno` (número).
Un ítem por turno: `pregunta`, `codigo` (lista), `resumen_resultados`, `respuesta`, `expira` (TTL). Un ítem por turno
mantiene cada uno lejos del límite de 400 KB de DynamoDB. La conversación pertenece a una `sesion`; el agente rechaza
una conversación de otra sesión.

**Límites de uso** (cuidan los créditos con muchas personas a la vez): máximo 30 preguntas por sesión al día y 20 turnos
por conversación (contados en DynamoDB), más la limitación de tasa de API Gateway.

## 6. Costos (para la AWS Pricing Calculator)

Precios de referencia de us-east-1; **se confirman al armar la estimación en la calculadora**.

| Recurso | Supuesto | Por hora | Por mes 24/7 |
|---|---|---|---|
| Fargate agente | 0,25 vCPU / 0,5 GB, 1 tarea (hasta 3 en picos) | ~US$0,012 | ~US$9 |
| Fargate sandbox | 0,5 vCPU / 1 GB, 1 tarea (hasta 3 en picos) | ~US$0,025 | ~US$18 |
| Endpoints de interfaz | 3 endpoints × 1 zona | ~US$0,030 | ~US$22 |
| IP pública del agente | 1 IPv4 por tarea | ~US$0,005 | ~US$3,6 |
| Lambda, API Gateway, DynamoDB, S3, ECR, Logs | uso de demo | ≈0 (capa gratuita) | <US$2 |
| Bedrock Haiku 4.5 | ~US$0,02–0,06 por pregunta (sube algo con el historial) | por uso | depende del uso |
| **Total infraestructura** | | **~US$0,07/h** | **~US$55/mes** |

Corrección a lo conversado: la estimación inicial (US$20–30/mes) no contaba los endpoints de VPC que exige un sandbox
sin internet. **Uso real del proyecto:** encendido solo para ensayos y demo (p. ej. 10 h en total ≈ US$0,70 + Bedrock).
En la presentación se muestran ambos escenarios: "siempre encendido" vs. "solo cuando se usa". Escenario de la demo
con el curso: ~30 personas × ~3 preguntas ≈ 90 preguntas ≈ US$2–5 en Bedrock, y los picos agregan tareas por minutos.

## 7. Terraform y estructura del repositorio

```
EntregaFinal/
  README.md                   Cómo levantar, probar y apagar
  docs/diseno-arquitectura.md Este documento
  arquitectura/arquitectura.drawio  Diagrama (y exportación .png)
  costos/                     Estimación: enlace de la calculadora + tabla + capturas
  app/agente/                 Python 3.12, Dockerfile
  app/sandbox/                Python 3.12 + pandas + matplotlib, Dockerfile
  app/lambdas/                archivos.py, trabajos.py
  web/                        index.html (+ JS) del chat
  terraform/                  red, ecr, ecs, api, lambdas, datos, iam, salidas
  datos-ejemplo/              CSV de ejemplo para la demo (datos ficticios)
```

- **Un solo comando:** Terraform construye y sube las imágenes a ECR durante el `apply` (proveedor `kreuzwerker/docker`
  usando el Docker del Codespace), y sube `web/` al bucket con la URL de la API ya inyectada.
- Salidas: `url_web`, `url_api`.
- Estado de Terraform local en el Codespace (no se sube al repo; `.gitignore` ya lo excluye). Riesgo: si el Codespace
  se borra antes de `terraform destroy`, los recursos quedan huérfanos cobrando ~US$0,07/h. Mitigación: todos los
  recursos llevan la etiqueta `Proyecto=analista-datos` para encontrarlos y borrarlos a mano; el README lo explica.
- Permisos de Bedrock del agente: `bedrock:InvokeModel` sobre el perfil de inferencia `global.` y los ARN del modelo
  base en todas las regiones (el perfil global enruta a cualquiera).

## 8. Decisiones del usuario

- Proyecto: analista de datos con IA (agente).
- Enfoque 1: agente y sandbox como servicios en ECS Fargate.
- Sin EC2; sin EventBridge, Billing ni Health; CloudWatch para logs (y las métricas del autoescalado).
- Proyecto "real": varias personas a la vez.
- Conversación con memoria.
- Sin Route 53 DNS Firewall: la fuga por DNS queda como riesgo documentado.
- Carpeta `EntregaFinal/` en el repo actual.

## 9. Decisiones mías (revisables)

- Sin balanceador ni NAT: VPC Link + Cloud Map y agente en subred pública, por costo.
- Patrón asíncrono (`202` + consulta cada 1–2 s) por el límite de 30 s de API Gateway.
- Sesión anónima por navegador; sin login.
- Límites: CSV ≤10 MB, 6 iteraciones, 30 s por ejecución, retención de 7 días.
- Endpoints de interfaz en una sola zona.
- Docker build dentro de Terraform para "un solo comando".
- Python 3.12 en los contenedores.
- Autoescalado 1–3 tareas por servicio en 2 zonas; sandbox con 4 ejecuciones simultáneas por tarea.
- Memoria: últimos 10 turnos, resultados resumidos a 1 500 caracteres; una conversación por CSV.
- Límites: 30 preguntas por sesión al día, 20 turnos por conversación.
- Sesión anónima aunque sea multiusuario: un usuario no puede ver los archivos de otro porque todo se separa por `sesion`
  (identificador aleatorio difícil de adivinar). Cognito quedaría como mejora futura.

## 10. Lo que queda al constructor

Nombres internos, estructura del código dentro de cada contenedor, diseño visual de la página, contenido exacto del
prompt del sistema, CSV de ejemplo, y los detalles de Terraform no fijados arriba.

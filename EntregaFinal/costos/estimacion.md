# Estimación de costos — Analista de datos con IA

Región: **us-east-1 (Norte de Virginia)**. Precios consultados el **26/11/2026** en la API oficial de precios de AWS
(`aws pricing get-products`, la misma fuente que usa la calculadora). Las cuentas de abajo se hacen con esos precios.

## Precios unitarios verificados

| Servicio | Concepto | Precio |
|---|---|---|
| AWS Fargate (Linux x86) | vCPU por hora | US$0,04048 |
| AWS Fargate (Linux x86) | GB de memoria por hora | US$0,004445 |
| VPC endpoints de interfaz | por endpoint por zona por hora | US$0,01 |
| VPC endpoints de interfaz | GB procesado | US$0,01 |
| IPv4 pública | por dirección en uso por hora | US$0,005 |
| Amazon Bedrock — Claude Haiku 4.5 (perfil global) | millón de tokens de entrada | US$1,00 |
| Amazon Bedrock — Claude Haiku 4.5 (perfil global) | millón de tokens de salida | US$5,00 |
| AWS Lambda | millón de solicitudes / GB-segundo | US$0,20 / US$0,0000166667 |
| API Gateway HTTP API | millón de solicitudes | US$1,00 |
| DynamoDB on-demand | millón de escrituras / lecturas | US$0,625 / US$0,125 |
| S3 Standard | GB-mes / 1 000 PUT-POST / 10 000 GET | US$0,023 / US$0,005 / US$0,004 |
| ECR | GB-mes almacenado | US$0,10 |
| CloudWatch Logs | GB ingerido / GB-mes almacenado | US$0,50 / US$0,03 |

## Lo que cobra por estar encendido

| Recurso | Configuración (lo que crea Terraform) | Por hora | 730 h (mes 24/7) |
|---|---|---|---|
| Fargate agente | 1 tarea · 0,25 vCPU · 0,5 GB | US$0,0123 | US$9,01 |
| Fargate sandbox | 1 tarea · 0,5 vCPU · 1 GB | US$0,0247 | US$18,02 |
| Endpoints de interfaz | 3 (`ecr.api`, `ecr.dkr`, `logs`) × 1 zona | US$0,0300 | US$21,90 |
| IPv4 pública del agente | 1 dirección | US$0,0050 | US$3,65 |
| **Subtotal fijo** | | **US$0,072** | **US$52,58** |

El endpoint de S3 es de tipo *gateway* y no cobra. El autoescalado puede subir a 3 tareas por servicio durante un pico;
cada tarea extra del sandbox cuesta US$0,025/h mientras exista.

## Lo que cobra por uso

**Bedrock por pregunta (estimación, no medición):** una pregunta típica hace 2–3 vueltas del ciclo (pensar → ejecutar → revisar).
Suponiendo ~12 000 tokens de entrada en total (prompt, resumen del CSV, historial y resultados) y ~2 000 de salida:
12 000 × US$1/M + 2 000 × US$5/M ≈ **US$0,022 por pregunta**. Con conversaciones largas (más historial) puede llegar a ~US$0,05.
Durante el ensayo conviene mirar el consumo real en CloudWatch (métricas de Bedrock `InputTokenCount` y `OutputTokenCount`) y corregir este supuesto.

Lambda, API Gateway, DynamoDB, S3 y Logs con el uso de una demo quedan en centavos (y casi todo entra en la capa gratuita).

## Escenarios

| Escenario | Infraestructura | Bedrock | Otros | **Total** |
|---|---|---|---|---|
| **Siempre encendido** (730 h, ~1 000 preguntas al mes) | US$52,58 | ~US$22 | ~US$1 | **~US$76/mes** |
| **Solo demo** (10 h encendido en total, ~90 preguntas: 30 personas × 3) | US$0,72 | ~US$2 | <US$0,10 | **~US$3** |

La diferencia entre los dos escenarios es el mensaje de costos de la presentación: en la nube se paga por tiempo
encendido, así que `terraform destroy` al terminar es parte del diseño.

## Cómo armarlo en la AWS Pricing Calculator

1. Entra a <https://calculator.aws/#/estimate> → **Create estimate**.
2. Agrega un grupo llamado `Analista de datos` y, dentro, cada línea de esta tabla con **Region = US East (N. Virginia)**.
   Escenario "siempre encendido" (para el de demo, cambia 730 h por 10 h y las cantidades de uso por las de la demo).

| # | Servicio a buscar | Descripción | Configuración |
|---|---|---|---|
| 1 | **AWS Fargate** | Agente | Linux, x86 · Number of tasks: 1 por mes · Average duration: 730 hours · vCPU: 0.25 · Memory: 0.5 GB · Ephemeral storage: 20 GB |
| 2 | **AWS Fargate** | Sandbox | Linux, x86 · Number of tasks: 1 por mes · Average duration: 730 hours · vCPU: 0.5 · Memory: 1 GB · Ephemeral storage: 20 GB |
| 3 | **Amazon Virtual Private Cloud (VPC)** | Endpoints e IPv4 | VPC Endpoints → Interface endpoints: Number of VPC interface endpoints per AZ: 3 · Number of AZs: 1 · Data processed: 1 GB por mes. Public IPv4 Addresses → In-use public IPv4 addresses: 1 |
| 4 | **Amazon Bedrock** | Claude Haiku 4.5 | Model provider: Anthropic · Model: Claude Haiku 4.5 · Inference route: Global · On Demand - Standard · Average requests per minute: 1 · Hours per day: 1 · Average input tokens per request: 6 667 · Average output tokens per request: 1 111 (ver nota) |
| 5 | **AWS Lambda** | `archivos` y `trabajos` | Architecture: x86 · Number of requests: 50 000 por mes · Duration: 100 ms · Memory: 256 MB · Ephemeral storage: 512 MB |
| 6 | **Amazon API Gateway** | HTTP API | HTTP APIs → Requests: 60 000 por mes · Average size: 4 KB |
| 7 | **Amazon DynamoDB** | `trabajos` y `conversaciones` | On-Demand · Data storage: 1 GB · Write request units: 20 000 por mes · Read request units: 60 000 por mes |
| 8 | **Amazon Simple Storage Service (S3)** | Sitio web y datos | S3 Standard · Storage: 1 GB · PUT/COPY/POST/LIST: 5 000 · GET/SELECT: 60 000 |
| 9 | **Amazon Elastic Container Registry** | Imágenes | Storage: 1 GB por mes |
| 10 | **Amazon CloudWatch** | Logs | Logs → Standard logs data ingested: 1 GB · Storage: 1 GB |

Supuestos de uso de las líneas 5–8 para ~1 000 preguntas al mes: cada pregunta consulta su estado cada 1,5 s durante
~30 s (≈ 20 llamadas a `trabajos`), más las subidas de CSV.

**Nota sobre Bedrock:** la calculadora no acepta menos de 1 solicitud por minuto ni horas con decimales, así que
1 000 preguntas × (12 000 tokens de entrada + 2 000 de salida) se expresa como 1 solicitud/min × 1 h/día × 30 días
= 1 800 solicitudes de 6 667 tokens de entrada y 1 111 de salida. Da lo mismo: 12 M de entrada + 2 M de salida = US$22,00.

3. **Save and share** → copia el enlace público y pégalo aquí:

**Enlace de la estimación:** <https://calculator.aws/#/estimate?id=e8a819d787a858744dc31b2b9ea11d3f88c76451>

Resultado en la calculadora (26/11/2026): **US$75,63 al mes** · US$907,56 en 12 meses · sin pago inicial.

| # | Línea | Mensual |
|---|---|---|
| 1 | Fargate sandbox | US$18,03 |
| 2 | Fargate agente | US$9,01 |
| 3 | VPC (endpoints + IPv4) | US$25,56 |
| 4 | Bedrock Haiku 4.5 | US$22,00 |
| 5 | Lambda | US$0,00 (capa gratuita) |
| 6 | API Gateway | US$0,06 |
| 7 | DynamoDB | US$0,30 |
| 8 | S3 | US$0,07 |
| 9 | ECR | US$0,10 |
| 10 | CloudWatch Logs | US$0,50 |

Si la calculadora da un total distinto al de la tabla de escenarios, manda la calculadora: puede incluir la capa gratuita
de otra forma o tener un precio actualizado.

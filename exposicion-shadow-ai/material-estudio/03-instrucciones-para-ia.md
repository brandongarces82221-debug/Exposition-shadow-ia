# Instrucciones para una IA que retome este proyecto

Lee este archivo completo antes de hacer cualquier cambio. Resume el contexto, las decisiones ya tomadas y lo que falta.

## Contexto

- **Qué es:** una exposición universitaria para la materia **Computación en la Nube**. Tema: **Ficha 4, "Shadow AI y ataques a la IA"**, de la guía `7 Temas de Exposición_ Cloud + IA.docx` (en la raíz del repo; incluye la estructura obligatoria y la rúbrica).
- **Idioma:** todo en **español** (Colombia). Responde al usuario en español.
- **Expositor único:** el usuario presenta **solo**, sin grupo. El guion y la guía están escritos en primera persona para una sola persona que habla y maneja la demo a la vez. No reintroduzcas repartos por integrante.
- **Formato exigido:** 15 a 20 minutos de exposición, 5 de demo, 5 a 10 de preguntas. Estructura: problema → cómo funciona → caso real → riesgos y dilemas → postura (la del expositor).
- **Repo:** https://github.com/brandongarces82221-debug/Exposition-shadow-ia (rama `main`).

## Restricciones del usuario (respetarlas)

1. **Cuenta de AWS con pocos créditos:** todo debe ser barato y liviano.
2. **Simple:** usar la **VPC por defecto**; no crear VPC, subredes, NAT ni balanceadores. "Solo es una demo."
3. **"Que solo sea levantarlo y que funcione":** un `terraform apply` debe dejar todo funcionando sin pasos manuales (salvo habilitar el modelo en Bedrock).
4. Infraestructura con **Terraform** (cuando el usuario dijo "tesseract" se refería a Terraform).
5. **La demo va al final** de la exposición y **las diapositivas no explican cómo se construyó la demo** (no hay diapositiva de arquitectura). La arquitectura queda solo en la guía de estudio por si preguntan.
6. **No hay diapositiva de postura ni de "lo que vimos en la demo"** (el usuario las quitó). La postura y la lección de las capas se dicen en voz alta en el cierre (diapositiva 12), porque la rúbrica da un 10 % a "Postura y cierre".

## Estructura del repo

Todo lo de esta exposición vive en la carpeta `exposicion-shadow-ai/`. La raíz del repo queda libre para otros proyectos.

```
README.md                               Índice del repo
.gitignore                              Excluye *.tfstate, .terraform/, *.tfvars
exposicion-shadow-ai/
  README.md                             Portada de la exposición
  7 Temas de Exposición_ ... .docx      Guía del profesor (fuente de los requisitos)
  presentacion/diapositivas.html        Las 12 diapositivas, se abren sin conexión (← → para avanzar, N para notas)
  presentacion/diapositivas.pptx        Las mismas 12 diapositivas en PowerPoint (las genera presentacion/construir_pptx.js con pptxgenjs)
  presentacion/fuente/                  Archivos fuente del deck (deck.json, deck.css, slides/*.html)
  demo-aws/
    README.md                           Cómo levantar, costos, guion de la demo, fallas comunes
    app/app.py                          Servidor HTTP (stdlib) + anthropic + boto3
    app/index.html                      Interfaz: chat, inyección indirecta, contadores, QR
    terraform/main.tf                   EC2, SG, IAM, Bedrock Guardrail
    terraform/variables.tf              region, instance_type, model_id, secret_code, allowed_cidr
    terraform/outputs.tf                url, guardrail_id, instance_id
    terraform/cloud-init.yaml.tftpl     Instala Python 3.11, la app y el servicio systemd
  material-estudio/                     Guion, guía de estudio y este archivo
  material-estudio.zip                  Los mismos tres archivos comprimidos
```

## Cómo funciona la demo "Hackea a Uni"

- El curso intenta que "Uni", el asistente de la Facultad, revele el código `DRAGON-7731` (ficticio, guardado a propósito en el prompt del sistema).
- **Modo "sin"**: el mensaje va directo al modelo. **Modo "con"**: `ApplyGuardrail` revisa la entrada (`source=INPUT`) y la salida (`source=OUTPUT`). Mismo prompt y mismo modelo en ambos modos: la única variable es el guardrail.
- Endpoints de `app.py`: `GET /`, `GET /health`, `GET /api/stats`, `GET /qr.svg` (QR con `http://<Host>`), `POST /api/chat`, `POST /api/resumir`, `POST /api/reset`.
- `MOCK=1` simula las respuestas sin AWS (para ensayar y para probar cambios localmente).
- El código se detecta en la salida normalizando a alfanumérico (`filtro_secreto`), y así se cuentan las "filtraciones".

## Decisiones técnicas ya tomadas (no cambiarlas sin preguntar)

| Decisión | Motivo |
|---|---|
| Modelo **Claude Haiku 4.5** con el perfil de inferencia `global.anthropic.claude-haiku-4-5-20251001-v1:0`, vía `AnthropicBedrock` (endpoint `bedrock-runtime`, InvokeModel) | Es el único modelo con el acuerdo `AVAILABLE` en la cuenta del usuario (Haiku 5.5, Sonnet 5 y otros dan `NOT_AVAILABLE`). El ID sin prefijo `global.`/`us.` falla (no admite throughput on-demand). Por `bedrock-mantle` da 403. |
| SDK fijado en `anthropic[bedrock]>=1.17,<2` (cloud-init) | La 2.x envía la versión de API `2026-10-21`, que Bedrock solo acepta para modelos 4.7+. Sin `effort` ni `thinking` (Haiku 4.5 no usa `effort`). Si algún día se cambia a un modelo 4.7+, se puede subir a la 2.x. |
| Guardrails con `ApplyGuardrail` en `bedrock-runtime` (boto3), separado de la llamada al modelo | Funciona independiente del endpoint del modelo y permite mostrar qué capa bloqueó. |
| Permisos de IAM: `bedrock:InvokeModel` (sobre `*`, porque el perfil global enruta a cualquier región) y `bedrock:ApplyGuardrail` (solo sobre el ARN del guardrail), más `AmazonSSMManagedInstanceCore` | Mínimo privilegio; SSM permite entrar sin abrir SSH. |
| EC2 `t3.micro`, Amazon Linux 2023, IMDSv2 obligatorio, servicio systemd con `DynamicUser` y `CAP_NET_BIND_SERVICE` en el puerto 80 | Simple y barato. |
| Archivos de la app como **texto plano** en `write_files` de cloud-init y user_data con `base64gzip` | El límite de user_data es 16 KB; ahora ocupa unos 8 KB. Si crecen mucho los archivos, revisar el tamaño. |
| Guardrail en versión `DRAFT` | Suficiente para la demo. |
| Políticas del guardrail: PROMPT_ATTACK (HIGH en entrada), tema prohibido "Credenciales internas" y regex generada desde `var.secret_code` que tolera separadores | Muestra tres capas distintas. |

## Diapositivas

- 12 diapositivas en un artefacto de Claude (privado): https://claude.ai/artifact/28BiHkCTfJozDXuNq4vouv
- Solo puede verlo o editarlo la cuenta del dueño, salvo que lo comparta desde **Share**. Si no tienes acceso, pide al usuario una exportación a PDF o PowerPoint.
- El guion (`01-guion-exposicion.md`) sigue el orden y el contenido de esas diapositivas.

## Estado y pendientes

**Verificado:**
- Se hizo un `terraform apply` real el 2026-11-26: la app quedó lista en ~1 minuto, los guardrails bloquearon en la entrada y el QR respondió. Luego se destruyó (`terraform destroy`).
- `terraform validate` y `terraform fmt` pasan con Terraform 1.17 y el proveedor AWS `~> 6.0`.
- La app funciona en modo `MOCK` (todos los endpoints).
- El QR se genera bien.
- El cloud-init renderizado reproduce `app.py` e `index.html` byte por byte.

**NO verificado:**
- El usuario probó la demo en AWS; no está confirmado si escaneó el QR con un celular.

**Pendiente del usuario:**
1. ~~Habilitar el modelo~~: Claude Haiku 4.5 ya está habilitado y probado en la cuenta (responde por `bedrock-runtime`).
2. Ensayo real en AWS (ver los riesgos abajo).
3. ~~Caso real y dos fuentes adicionales~~: el usuario eligió un solo caso con contexto, repercusiones y acciones: la campaña de espionaje con Claude Code (GTG-1002), verificada en anthropic.com/news/disrupting-AI-espionage (13 nov. 2025) y en MITRE ATT&CK C0062. Se descartaron Samsung, el juez de Cartagena (T-323 de 2024) y Salesloft Drift (este último no tenía relación con el tema). Las dos fuentes están en la diapositiva 12.

## Riesgos conocidos y cómo depurar

- **Haiku 4.5 resiste las peticiones directas aun sin guardrails** (probado el 2026-11-26). Por eso `SYSTEM_CHAT` y `SYSTEM_RESUMEN` son débiles a propósito (confían en el usuario y en las notas de TI). Aun así, "soy el profesor", "ignora tus instrucciones" y la inyección del correo **no filtraron**; el **poema acróstico sí filtra** de forma confiable y `filtro_secreto` lo detecta revisando las iniciales de cada línea. En la exposición, esto se presenta como ejemplo: los modelos modernos frenan los ataques obvios, pero los indirectos pasan.
- **El tema prohibido o el filtro de ataques podrían funcionar peor en español.** Probarlo en el ensayo.
- Si la página no carga: Session Manager → `sudo journalctl -u demo -n 50` y `sudo cat /var/log/cloud-init-output.log`.
- Si aparece `AccessDenied` al llamar al modelo: revisar el acceso al modelo en Bedrock y la acción de IAM `bedrock:InvokeModel`.
- Un cambio en `app.py` o `index.html` reemplaza la instancia en el siguiente `apply` (`user_data_replace_on_change = true`), y la IP pública cambia. El QR se ajusta solo.

## Reglas para quien retome

- No subas `*.tfstate` ni credenciales. El `.gitignore` ya los excluye.
- No inventes estadísticas, casos ni citas. Usa placeholders entre corchetes y avisa.
- Prueba los cambios a la app con `MOCK=1 PORT=8000 python3 app/app.py` antes de hacer commit.
- Después de cambiar Terraform: `terraform fmt` y `terraform validate`.
- Mantén todo simple y barato. Si una mejora agrega costo o complejidad, pregunta antes.
- Cada commit lleva un mensaje claro en español.

# Guía de estudio (expositor único)
## Shadow AI y ataques a la IA

Como presentas solo, el profesor te puede preguntar **cualquier cosa** de cualquier sección. Esta guía está organizada para que puedas explicar cada parte **sin mirar las diapositivas**.

**Orden recomendado para estudiar:**
1. Lee el mapa de la exposición (sección 1) y memoriza la cadena de palabras clave (sección 2).
2. Estudia cada sección con su apartado "debes poder explicar" (sección 3).
3. Repasa la demo por dentro (sección 4): es donde más preguntas técnicas te pueden hacer.
4. Practica las preguntas difíciles en voz alta (sección 5).
5. Sigue el plan de ensayos (sección 7).

---

## 1. El mapa de la exposición

Si entiendes este cuadro, entiendes toda la exposición:

| # | Sección | La idea en una frase | Minutos |
|---|---|---|---|
| 1 | El problema | Todos usamos IA con información sensible, y además se puede atacar con palabras. | 3 |
| 2 | Cómo funciona | Para el modelo, las reglas y los datos son el mismo texto; por eso se le engaña. | 6 |
| 3 | Caso real y riesgos | El ataque con palabras ya pasó (espías engañaron a Claude Code); prohibir no basta y hay datos que nunca se comparten. | 3,5 |
| 4 | Demo | El curso ataca a Uni: sin protección cae, con guardrails resiste mucho mejor. | 5,5 |
| 5 | Cierre | Ninguna capa basta sola; mi postura: habilitar con reglas. ¿IA más segura o usuarios mejor preparados? | 1 |

**La tesis de toda la exposición (apréndela de memoria):**
> "Para una IA, las instrucciones y los datos son el mismo texto. Por eso se puede engañar con palabras, y por eso la defensa no puede ser una sola capa: hacen falta filtros, buen diseño y personas preparadas."

---

## 2. Cadena de palabras clave (para no perderte)

Una palabra o frase por diapositiva. Repítela en orden hasta que te salga sola: si recuerdas la cadena, recuerdas la exposición.

```
 1 Pregunta        →  ¿hackear con palabras?
 2 Escenario       →  contrato pegado · nadie la atacó
 3 Dos frentes     →  adentro nosotros · afuera atacante
 4 Todo es texto   →  un solo bloque · empleado nuevo
 5 Inyección       →  directa vs escondida · OWASP n.º 1
 6 Técnicas        →  autoridad · rol · disfraz · anular
 7 Agentes         →  dice vs hace
 8 Caso real       →  "somos de seguridad" · 80–90 % · una mentira
 9 Shadow AI       →  prohibir o habilitar · señal de demanda
10 Nunca pegar     →  4 cosas · WhatsApp de 500
11 DEMO            →  QR · ronda 1 · ronda 2 · correo
12 Cierre          →  ninguna capa basta sola · habilitar con reglas · ¿IA segura o usuarios preparados?
```

**Truco para tu postura (la dices en el cierre, diapositiva 12):** las iniciales **H-C-G-H-P-R** → "**H**ay **C**osas **G**randes **H**oy **P**ara **R**evisar".

**Truco para las técnicas (diapositiva 6):** "**A**l **R**ector lo **D**isfrazaron **A**nulando" → **A**utoridad, **R**ol, **D**isfraz, **A**nular.

---

## 3. Sección por sección: lo que debes poder explicar

### Sección 1 · El problema

**Debes poder explicar sin diapositivas:**
- Qué es el **Shadow AI** y un ejemplo cotidiano.
- Por qué la gente lo hace (ahorrar tiempo, no mala intención).
- La diferencia entre el riesgo **hacia adentro** (nosotros entregamos datos) y **hacia afuera** (alguien ataca la IA).

**Definición para decir de memoria:**
> "Shadow AI es el uso de herramientas de inteligencia artificial por fuera del control y la aprobación del área de tecnología, normalmente entregándoles información de la organización."

**Si te preguntan:**
- *"¿El Shadow AI es lo mismo que el Shadow IT?"* → "Es un caso particular. El Shadow IT es usar cualquier software sin aprobación, como un Dropbox personal. El Shadow AI es lo mismo con herramientas de IA, pero más delicado, porque lo que se les entrega es justamente información para que la procesen."

### Sección 2 · Cómo funciona

**Debes poder explicar sin diapositivas:**
- Las tres entradas del modelo: instrucciones del sistema, mensaje del usuario y documentos.
- Por qué "todo es texto" permite el ataque.
- La analogía del empleado nuevo y la comparación con SQL injection.
- Inyección **directa** vs **indirecta**, con un ejemplo de cada una.
- Las cuatro técnicas de jailbreak.
- Por qué el riesgo crece con los **agentes**.

**Conceptos clave:**

| Concepto | Explicación sencilla |
|---|---|
| **Modelo de lenguaje (LLM)** | Programa entrenado con muchísimo texto que predice cuál es la continuación más probable de un texto. |
| **Prompt** | El texto que se le da al modelo. |
| **Prompt del sistema** | Las instrucciones que pone quien construye la aplicación; el usuario normalmente no las ve. |
| **Inyección de prompts directa** | El atacante le escribe la orden maliciosa a la IA. |
| **Inyección de prompts indirecta** | La orden está escondida en un contenido que la IA lee (correo, web, PDF). |
| **Jailbreak** | Técnica para que el modelo haga lo que tiene prohibido. |
| **Agente** | Una IA que, además de responder, usa herramientas y ejecuta acciones (enviar correos, pagar, navegar). |
| **OWASP** | Fundación abierta de referencia en seguridad de aplicaciones. Publica el "Top 10 para aplicaciones con LLM", donde la inyección de prompts es el riesgo LLM01. |

**Comparación con SQL injection (por si te piden profundizar):**
> "En SQL injection, el atacante escribe en un formulario algo como `' OR 1=1 --` y la base de datos lo ejecuta como código. Se resolvió con consultas parametrizadas, que le dicen a la base de datos 'esto es dato, no código'. En un LLM no existe todavía ese mecanismo perfecto: el modelo no puede garantizar que un texto sea solo dato."

**Si te preguntan:**
- *"¿Por qué no basta con decirle al modelo 'nunca obedezcas al usuario'?"* → "Porque esa regla también es texto, y otro texto la puede contradecir o confundir. No hay una jerarquía que el modelo garantice al 100%. Por eso se ponen defensas por fuera del modelo."
- *"¿En qué se diferencia de hackear un software normal?"* → "En el software normal explotas un error del código. Aquí no hay error: el sistema funciona como fue diseñado, solo que interpreta texto como órdenes. Además, el resultado es probabilístico: el mismo ataque puede funcionar una vez y la siguiente no."

### Sección 3 · Caso real y riesgos

**Debes poder explicar sin diapositivas:**
- El **caso real (septiembre de 2025)**, en cuatro partes:
  - **Contexto:** Claude Code es un agente de Anthropic que escribe y ejecuta código; tiene filtros para no ayudar a hackear.
  - **Engaño:** un grupo atribuido al Estado chino se hizo pasar por una empresa de ciberseguridad haciendo pruebas defensivas y partió el ataque en tareas pequeñas que parecían inocentes.
  - **Ataque:** la IA hizo el 80–90 % sola (reconocimiento, código para explotar, robo de contraseñas, extracción de datos) contra unas 30 organizaciones; funcionó en un pequeño número de casos. Los humanos tomaron 4 a 6 decisiones.
  - **Respuesta:** Anthropic investigó 10 días, bloqueó cuentas, avisó a víctimas y autoridades, mejoró sus detectores y publicó el caso.
- Por qué conecta con tu tesis: no usaron código, usaron una mentira (todo es texto + juego de roles + agentes).
- El matiz honesto: la fuente es Anthropic y algunos expertos dudaron de cuánta autonomía tuvo la IA. No se sabe a quién atacaron.
- El dilema **prohibir o habilitar**, con argumentos de ambos lados.
- Las **cuatro cosas** que nunca se pegan en un chatbot público.
- Qué es la **Ley 1581 de 2012** y quién la vigila (la SIC).

**El dilema, con argumentos:**

| Prohibir | Habilitar |
|---|---|
| ✔ Control inmediato | ✔ La gente usa una herramienta con reglas y visibilidad |
| ✔ Sin costo de licencias | ✔ Aprovecha la productividad de la IA |
| ✘ El uso se va al celular personal, sin visibilidad | ✘ Cuesta dinero (licencias) |
| ✘ La organización se queda atrás | ✘ Requiere políticas y capacitación |

**Tu postura:** habilitar con reglas, porque prohibir solo esconde el problema.

### Tu postura (ya no tiene diapositiva: la dices en el cierre)

**Debes poder decir los seis puntos de memoria** (truco H-C-G-H-P-R):
1. **H**abilitar, no prohibir.
2. **C**lasificar los datos con un semáforo.
3. **G**uardrails en todo asistente propio.
4. **H**umano en el ciclo para acciones.
5. **P**racticar: capacitar con demos como la de hoy.
6. **R**evisar la política cada semestre.

**Si te preguntan "¿y eso no es muy caro?":** "Una licencia institucional cuesta, pero mucho menos que una fuga de datos personales sancionada bajo la Ley 1581, sin contar el daño a la reputación."

---

### Sección 4 · La demo (va al final)

**Debes poder explicar sin diapositivas:**
- Qué es Uni y cuál es el reto (sacarle el código `DRAGON-7731`).
- Qué cambia entre la ronda 1 y la ronda 2 (**solo** el guardrail).
- Qué es un **guardrail** y qué revisa (la entrada y la salida).
- Cómo funciona la inyección indirecta del correo.

**Por qué el experimento es justo:** las dos rondas usan el **mismo modelo y el mismo prompt**. Lo único que cambia es el guardrail. Es como un experimento controlado: así sabemos que la diferencia la hizo esa capa.

**Si la demo no sale como esperabas:**

| Qué pasó | Qué dices |
|---|---|
| Nadie sacó el código en la ronda 1 | "El modelo ya trae resistencia de fábrica. Pero ¿confiarían una empresa solo en eso? Por eso se agregan capas." |
| Un ataque pasó con guardrails | "Esto demuestra que los guardrails reducen el riesgo, pero no lo eliminan. Por eso hacen falta las capas de diseño." |
| El guardrail bloqueó algo inocente | "Esto se llama **falso positivo**: el filtro se equivocó para el lado seguro. Es el costo de un filtro estricto: equilibrar seguridad y utilidad." |
| AWS no responde | Pasar al modo simulado (MOCK) y explicarlo con naturalidad. |

### Lo que aprendimos: las capas (las dices en el cierre), y cómo está montada la demo

*Ni la arquitectura ni las capas tienen diapositiva, pero te las pueden preguntar: apréndete el recorrido.*

**Debes poder explicar sin diapositivas:** el recorrido completo de un mensaje y las seis capas.

**El recorrido de un mensaje:**
```
Celular ──► EC2 t3.micro (VPC por defecto, app en Python)
                 ├─► 1. Guardrail revisa la ENTRADA
                 ├─► 2. Claude Haiku en Amazon Bedrock responde
                 └─► 3. Guardrail revisa la SALIDA ──► vuelve al celular
```

**Las seis capas:**

| # | Capa | Tipo | Qué hace |
|---|---|---|---|
| 1 | Detector de ataques de prompt | Guardrail | Reconoce frases tipo "ignora tus instrucciones" en la entrada. |
| 2 | Tema prohibido | Guardrail | Bloquea pedir credenciales o códigos internos, aunque sea con amabilidad. |
| 3 | Filtro de datos sensibles | Guardrail | Una expresión regular atrapa el código en la salida, incluso deletreado. |
| 4 | Sin secretos en el prompt | Diseño | Lo que el modelo no sabe, no lo puede filtrar. |
| 5 | Permisos mínimos | Diseño | Si engañan al agente, que pueda hacer poco daño. |
| 6 | Humano en el ciclo | Diseño | Una persona aprueba antes de pagar, borrar o enviar. |

**Frase clave:** "Defensa en profundidad: ninguna capa es perfecta, pero juntas hacen que el ataque sea mucho más difícil. Igual que un antivirus más un firewall más una contraseña fuerte."

## 4. La demo por dentro (preguntas técnicas)

Como es una materia de nube, el profesor puede preguntarte **cómo lo construiste**. Esto es lo que debes saber.

### Los recursos que crea Terraform

| Recurso | Qué es | Concepto de la materia |
|---|---|---|
| `aws_instance` (EC2 t3.micro) | Máquina virtual con Amazon Linux 2023 que corre la app. | Cómputo, IaaS. |
| VPC por defecto | La red que ya trae toda cuenta de AWS. No creé red nueva para mantenerlo simple. | Redes. |
| `aws_security_group` | Firewall de la máquina: solo deja entrar por el puerto 80 (HTTP). | Seguridad de red. |
| `aws_iam_role` + perfil de instancia | Le da permisos a la máquina sin poner llaves en el código. | Identidad, mínimo privilegio. |
| `aws_bedrock_guardrail` | El filtro con sus tres políticas. | Seguridad de IA. |
| user_data (cloud-init) | Script que corre al arrancar: instala Python, copia la app y la deja como servicio. | Automatización, bootstrapping. |

### Preguntas técnicas probables

**"¿Qué es Terraform y por qué lo usaste?"**
> "Es una herramienta de infraestructura como código: describo en archivos qué recursos quiero y Terraform los crea, modifica o borra. Lo usé porque con un solo comando levanto todo y con otro lo destruyo, sin hacer clics en la consola; así no se me olvida apagar nada y no gasto créditos."

**"¿Qué es Amazon Bedrock?"**
> "Es el servicio administrado de AWS para usar modelos de IA de varios proveedores sin administrar servidores ni GPU. Se paga por token, es decir, por la cantidad de texto que entra y sale."

**"¿Por qué Claude Haiku y no un modelo más grande?"**
> "Por costo y velocidad. Haiku es el modelo más económico de Claude y para un chat corto es suficiente. Es una decisión de FinOps: elegir el modelo adecuado para la tarea, no el más grande."

**"¿Cómo se conecta la máquina a Bedrock sin contraseñas?"**
> "Con un rol de IAM asociado a la instancia. AWS le entrega credenciales temporales a la máquina de forma automática. El rol solo tiene dos permisos: invocar el modelo y aplicar el guardrail. Además activé IMDSv2, que protege esas credenciales temporales contra ataques que intentan robarlas."

**"¿Qué es IMDSv2?"**
> "Es la versión 2 del servicio de metadatos de la instancia, de donde la máquina obtiene sus credenciales temporales. La v2 exige un token de sesión, lo que protege contra ataques SSRF que intentan leer esas credenciales desde afuera."

**"¿Cómo funciona el guardrail técnicamente?"**
> "La app llama a la API `ApplyGuardrail` dos veces: una con el mensaje del usuario como entrada, antes del modelo, y otra con la respuesta del modelo como salida. Si el guardrail interviene, devuelve un mensaje de bloqueo y la razón, y eso es lo que se muestra en pantalla."

**"¿Cómo detecta el código aunque lo deletreen?"**
> "Con una expresión regular que Terraform genera a partir del código. Acepta mayúsculas o minúsculas y hasta tres caracteres de separación entre cada letra. Así atrapa `DRAGON-7731`, `dragon7731` o `d r a g o n 7 7 3 1`."

**"¿Cuánto cuesta?"**
> "La t3.micro cuesta alrededor de un centavo de dólar por hora, más medio centavo por la IP pública. Haiku y el guardrail se cobran por uso, y en una clase se consume muy poco. En total, menos de diez centavos si la destruyo al terminar."

**"¿Por qué no usaste Lambda o contenedores?"**
> "Por simplicidad: es una demo de cinco minutos y una sola máquina en la VPC por defecto es lo más fácil de entender y depurar. En producción usaría algo serverless, como API Gateway con Lambda, o un balanceador con HTTPS."

**"¿Qué cambiarías para producción?"**
> "Sacar el secreto del prompt, poner HTTPS y autenticación de usuarios, limitar la cantidad de peticiones por usuario, monitorear con CloudWatch, fijar una versión publicada del guardrail en vez del borrador y hacer pruebas de ataque periódicas, lo que se llama red teaming."

**"¿Es segura la demo si está abierta a internet?"**
> "Está abierta solo durante la clase, sin datos reales: el código es inventado. La máquina tiene permisos mínimos y la destruyo al terminar. Para algo real pondría HTTPS, autenticación y límites de uso."

**"¿La IA aprende de lo que le escribieron en la demo?"**
> "No. El modelo no se reentrena con cada mensaje. Con los chatbots públicos gratuitos, en cambio, depende de los términos del servicio: algunos pueden usar las conversaciones para mejorar sus modelos, y eso es parte del riesgo del Shadow AI."

---

## 5. Preguntas difíciles

**"¿Quién es responsable si un agente filtra datos por una inyección?"**
> "No hay una respuesta única todavía, y es un debate abierto. Mi postura es que la responsabilidad principal es de quien despliega el agente, porque decide qué permisos le da y qué controles le pone. El proveedor del modelo responde si su sistema tenía fallas conocidas, y el empleado, si ignoró las políticas."

**"Si los guardrails fallan, ¿para qué sirven?"**
> "Para reducir el riesgo y hacer el ataque más costoso. Ninguna medida de seguridad es perfecta, ni un antivirus ni un firewall, pero juntas hacen la diferencia. Por eso hablo de capas."

**"¿Esto no le enseña a la gente a atacar?"**
> "Los ataques que mostré son públicos y conocidos, y los hice en un sistema propio. El objetivo es el mismo de un simulacro de phishing en una empresa: si no sabes cómo te atacan, no te puedes defender."

**"¿Qué opinas de prohibir la IA en la universidad?"**
> "Que no funcionaría: los estudiantes la usarían igual desde su celular. Prefiero habilitarla con reglas claras y enseñar a usarla bien."

### Si no sabes la respuesta
No inventes. Usa una de estas fórmulas:
- "Muy buena pregunta. No lo investigué a ese nivel, pero lo que sí sé es que… *(conecta con algo que domines)*."
- "No tengo el dato exacto aquí, prefiero no inventarlo. Lo verifico y se lo comparto."

---

## 6. Datos y números para memorizar

| Dato | Valor |
|---|---|
| Riesgo n.º 1 de OWASP para aplicaciones con LLM | Inyección de prompts (LLM01) |
| Ley de protección de datos personales en Colombia | Ley 1581 de 2012 (la vigila la SIC) |
| Caso real | Septiembre 2025 (publicado el 13 nov. 2025): espías engañaron a Claude Code → ~30 organizaciones, la IA hizo el 80–90 %, 4 a 6 decisiones humanas |
| Catálogo MITRE ATT&CK | Campaña C0062 |
| Código secreto de la demo | `DRAGON-7731` (ficticio) |
| Máquina de la demo | EC2 t3.micro, Amazon Linux 2023, VPC por defecto, puerto 80 |
| Modelo | Claude Haiku 4.5 en Amazon Bedrock |
| Costo de la demo | Menos de US$0,10 por clase |
| Tiempo de arranque | Unos 2 minutos después de `terraform apply` |
| Capas de defensa | 6: tres del guardrail y tres de diseño |

---

## 7. Plan de ensayos

| Cuándo | Qué hacer |
|---|---|
| **5 días antes** | Lee el guion completo dos veces. Memoriza la tesis y la cadena de palabras clave. |
| **4 días antes** | Ensayo 1 en voz alta con las diapositivas, **leyendo** el guion. Cronométralo. |
| **3 días antes** | Haz el **ensayo real en AWS**: `terraform apply`, prueba las dos rondas, el QR con tu celular y la inyección del correo. Anota qué ataques funcionaron. Luego `terraform destroy`. |
| **2 días antes** | Ensayo 2 **sin leer**, solo con las palabras clave. Grábate con el celular y revisa en qué partes dudas. |
| **1 día antes** | Ensayo 3 completo, con la demo en modo MOCK. Practica las preguntas difíciles en voz alta. |
| **El día** | Repasa solo la cadena de palabras clave y la tesis. Llega 30 minutos antes para levantar la demo. |

**Consejos para presentar solo:**
- **Habla más despacio de lo que crees.** Los nervios aceleran; la diapositiva 4 merece ir lento.
- **Mira al curso, no a la pantalla.** Las diapositivas son tu apoyo, no tu guion.
- **Las pausas no son silencios incómodos:** le dan peso a lo que acabas de decir.
- **En la demo, narra lo que haces** ("ahora enciendo el interruptor…"): así nadie se pierde mientras manejas el computador.
- **Si te equivocas, sigue.** El curso no conoce tu guion; nadie nota lo que te saltaste.
- **Bebe agua entre secciones**, por ejemplo antes de la demo.

---

## 8. Lista de verificación final

**Contenido (antes del día):**
- [ ] Ensayo real en AWS hecho y el QR probado con un celular.

**El día:**
- [ ] `terraform apply` hecho y la página abre.
- [ ] Dos intentos de prueba: con y sin guardrails.
- [ ] Contadores en cero ("Limpiar chat y contadores").
- [ ] Interruptor de guardrails APAGADO para empezar.
- [ ] Solo dos pestañas abiertas: presentación y demo.
- [ ] Zoom de la demo aumentado.
- [ ] Celular en silencio y agua a mano.
- [ ] Al terminar: `terraform destroy`.

---

## 9. Rúbrica: cómo cubres cada criterio

| Criterio | Peso | Dónde lo cubres | Qué no puede faltar |
|---|---|---|---|
| Claridad conceptual | 20% | Diapositivas 4 a 7 | La analogía del empleado nuevo y "todo es texto" |
| Datos y fuentes | 15% | Diapositivas 5, 8, 10 y 12 | OWASP, Ley 1581, Anthropic (13 nov. 2025) y MITRE ATT&CK C0062 |
| Caso real | 15% | Diapositiva 8 | El ataque con Claude Code: contexto, engaño, ataque y respuesta |
| Demo o actividad | 20% | Diapositiva 11 y la página | Que el curso participe y vea la diferencia entre rondas |
| Análisis crítico y ética | 15% | Diapositiva 9 y el cierre | El dilema prohibir o habilitar y "ninguna capa basta sola" (dicho en el cierre) |
| Postura y cierre | 10% | Diapositiva 12 (en voz alta) | Tu postura en pocas frases y la pregunta de debate |
| Tiempo y presentación | 5% | Todo | Terminar en unos 19 minutos y responder con calma |

# Demo: ¿Se puede hackear una IA solo con palabras?

El curso intenta que **Uni**, el asistente de la Facultad, revele el código del laboratorio (`DRAGON-7731`).
Hay dos rondas con el **mismo modelo y el mismo prompt**: primero sin protección y después con
**Amazon Bedrock Guardrails**. La única diferencia entre las dos es el guardrail.

```
Navegador (curso) ──HTTP──► EC2 t3.micro (VPC por defecto)
                               │  app.py
                               ├─► Bedrock Guardrails  (revisa entrada y salida)
                               └─► Claude Haiku 5.5 en Bedrock
```

## Qué crea Terraform

| Recurso | Para qué |
|---|---|
| 1 EC2 `t3.micro` en la **VPC por defecto** | Sirve la página y llama a Bedrock |
| 1 Security Group | Abre solo el puerto 80 |
| 1 Rol IAM + perfil | Permisos para usar el modelo y el guardrail (sin llaves en el código) |
| 1 Bedrock Guardrail | Detector de ataques de prompt + tema prohibido + regex del código |

No se crean VPC, subredes, NAT ni balanceadores.

## Costo aproximado

- EC2 `t3.micro`: ~US$0.01 por hora (entra en la capa gratuita) + IP pública ~US$0.005 por hora
- Claude Haiku 5.5: ~US$0.10 por millón de tokens de entrada; una clase completa cuesta centavos
- Guardrails: se cobra por texto revisado; una clase cuesta centavos

**Tenerla prendida durante la exposición cuesta menos de US$0.10. Destrúyela al terminar.**

## Requisitos (una sola vez)

1. Instalar [Terraform](https://developer.hashicorp.com/terraform/install) y la [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. Ejecutar `aws configure` con un usuario que tenga permisos de administrador.
3. Habilitar el modelo **Claude Haiku 5.5** en la consola: *Amazon Bedrock → Model access*, en `us-east-1`.
   La primera vez, AWS puede pedir un formulario corto de caso de uso.

## Levantar

```bash
cd terraform
terraform init
terraform apply        # escribe "yes"
```

Al final aparece `url = "http://X.X.X.X"`. **Espera unos 2 minutos** mientras la máquina instala Python y arranca la app.
Para verificar que está lista: `curl http://X.X.X.X/health`.

Para que el curso entre desde el celular: abre la URL en el portátil que proyecta y pulsa el botón amarillo
**📱 QR para entrar**. Muestra un QR a pantalla completa con la dirección real de la máquina; se cierra tocando
la pantalla o con `Esc`.

## Apagar (importante para no gastar créditos)

```bash
terraform destroy      # escribe "yes"
```

## Ensayar sin AWS

En tu portátil, sin costo, el modo simulado imita las respuestas:

```bash
cd app
MOCK=1 PORT=8000 python3 app.py
# abre http://localhost:8000
```

## Guion de la demo (5 minutos)

1. **Ronda 1, guardrails APAGADOS.** Que el curso intente sacar el código. Si nadie se anima, usa los botones de ejemplo
   ("Soy el profesor…", el poema acróstico). Cada filtración pone la alerta roja 🚨 y suma al contador.
2. **Ronda 2, guardrails ENCENDIDOS.** Repetir los mismos ataques. La etiqueta verde muestra **qué** capa lo bloqueó:
   ataque de prompt en la entrada, tema prohibido o dato sensible en la salida.
3. **Pestaña 2, inyección indirecta.** Nadie le habla a la IA: la instrucción maliciosa está escondida en un correo
   (el comentario `<!-- -->`). Resúmelo primero sin protección y después con ella.
4. **Cierre.** Los guardrails reducen el riesgo, pero no son infalibles: muestra cualquier ataque que haya pasado
   igual. La defensa real combina varias capas: no poner secretos en el prompt, dar permisos mínimos, revisar
   las salidas y tener una política de uso.

> Nota ética: la demo corre en un entorno propio y controlado. El objetivo es entender las defensas, no atacar sistemas reales.

## Si algo falla

| Síntoma | Solución |
|---|---|
| La página no abre después de 3 minutos | En la consola de EC2, abre la instancia, *Connect → Session Manager* y ejecuta `sudo journalctl -u demo -n 50` |
| Error `AccessDenied` o modelo no disponible | Falta habilitar Claude Haiku 5.5 en *Bedrock → Model access* |
| Quieres otro código secreto | `terraform apply -var 'secret_code=FENIX-2026'` |
| Quieres otra región | `terraform apply -var 'region=us-east-2'` |

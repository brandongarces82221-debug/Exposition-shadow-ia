# ¿Se puede hackear una IA solo con palabras?

Exposición de Computación en la Nube, **Ficha 4: Shadow AI y ataques a la IA**.

| Carpeta / archivo | Contenido |
|---|---|
| [`presentacion/diapositivas.html`](presentacion/diapositivas.html) | Las 15 diapositivas en un solo archivo: descárgalo y ábrelo en el navegador. ← → para avanzar, **N** para ver las notas, **F** para pantalla completa. La fuente editable está en `presentacion/fuente/` (`python3 presentacion/construir.py` regenera el HTML). |
| [`demo-aws/`](demo-aws/) | Demo en vivo “Hackea a Uni”: app en Python + Terraform para AWS (EC2 en la VPC por defecto, Claude Haiku en Bedrock y Bedrock Guardrails). Instrucciones en su [README](demo-aws/README.md). |
| [`material-estudio/`](material-estudio/) | Guion, guía de estudio e instrucciones para IA (también en `material-estudio.zip`). |
| `material-estudio.zip` | Guion completo para expositor único (con tiempos y palabras clave), guía de estudio con preguntas probables e instrucciones para que una IA retome el proyecto. |
| `7 Temas de Exposición_ Cloud + IA.docx` | Guía original con los siete temas y la rúbrica. |

Inicio rápido de la demo:

```bash
cd exposicion-shadow-ai/demo-aws/terraform   # desde la raíz del repo
terraform init && terraform apply   # imprime la URL
terraform destroy                   # al terminar, para no gastar créditos
```

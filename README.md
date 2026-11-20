# ¿Se puede hackear una IA solo con palabras?

Exposición de Computación en la Nube, **Ficha 4: Shadow AI y ataques a la IA**.

| Carpeta / archivo | Contenido |
|---|---|
| [`demo-aws/`](demo-aws/) | Demo en vivo “Hackea a Uni”: app en Python + Terraform para AWS (EC2 en la VPC por defecto, Claude Haiku en Bedrock y Bedrock Guardrails). Instrucciones en su [README](demo-aws/README.md). |
| `material-estudio.zip` | Guion de la exposición por integrante, guía de estudio con preguntas probables e instrucciones para que una IA retome el proyecto. |
| `7 Temas de Exposición_ Cloud + IA.docx` | Guía original con los siete temas y la rúbrica. |

Inicio rápido de la demo:

```bash
cd demo-aws/terraform
terraform init && terraform apply   # imprime la URL
terraform destroy                   # al terminar, para no gastar créditos
```

"""Genera arquitectura.drawio (diagrama de la arquitectura en AWS).

Uso: python3 generar_diagrama.py  ->  escribe arquitectura.drawio al lado de este archivo.
Ábrelo en https://app.diagrams.net (Archivo > Abrir) o en draw.io Desktop.
"""
from pathlib import Path
from xml.sax.saxutils import escape

celdas = []
n = [1]


def nid():
    n[0] += 1
    return f"c{n[0]}"


PTS = "points=[[0,0,0],[0.25,0,0],[0.5,0,0],[0.75,0,0],[1,0,0],[0,1,0],[0.25,1,0],[0.5,1,0],[0.75,1,0],[1,1,0],[0,0.25,0],[0,0.5,0],[0,0.75,0],[1,0.25,0],[1,0.5,0],[1,0.75,0]];"


def caja(texto, x, y, w, h, estilo):
    i = nid()
    celdas.append(f'<mxCell id="{i}" value="{escape(texto, {chr(34): "&quot;"})}" style="{estilo}" vertex="1" parent="1">'
                  f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
    return i


def grupo(texto, x, y, w, h, gr_icon, trazo, relleno="none", color_texto="#232F3E", punteado=0):
    estilo = (f"{PTS}outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=13;fontStyle=1;"
              f"container=0;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
              f"grIcon=mxgraph.aws4.{gr_icon};strokeColor={trazo};fillColor={relleno};verticalAlign=top;"
              f"align=left;spacingLeft=30;fontColor={color_texto};dashed={punteado};")
    return caja(texto, x, y, w, h, estilo)


def recuadro(texto, x, y, w, h, trazo, color_texto, punteado=1, relleno="none"):
    estilo = (f"fillColor={relleno};strokeColor={trazo};dashed={punteado};verticalAlign=top;fontStyle=1;"
              f"fontColor={color_texto};whiteSpace=wrap;html=1;fontSize=13;align=center;")
    return caja(texto, x, y, w, h, estilo)


def icono(texto, x, y, res, color, tam=64, forma="resourceIcon", derecha=False):
    if forma == "resourceIcon":
        f = f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};"
    else:
        f = f"shape=mxgraph.aws4.{res};"
    estilo = (f"sketch=0;{PTS}outlineConnect=0;fontColor=#232F3E;fillColor={color};strokeColor=#ffffff;dashed=0;"
              + ("labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=4;"
                 if derecha else "verticalLabelPosition=bottom;verticalAlign=top;align=center;")
              + f"html=1;fontSize=12;fontStyle=0;"
              f"aspect=fixed;{f}")
    return caja(texto, x, y, tam, tam, estilo)


def nota(texto, x, y, w, h, relleno="#FFF4E5", trazo="#ED7100"):
    estilo = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={relleno};strokeColor={trazo};fontSize=12;"
              f"align=left;spacingLeft=8;spacingRight=8;arcSize=6;")
    return caja(texto, x, y, w, h, estilo)


def flecha(a, b, texto="", punteada=False, color="#232F3E", salida=None, entrada=None, puntos=None):
    i = nid()
    estilo = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;strokeWidth=2;"
              f"strokeColor={color};fontSize=11;fontColor=#232F3E;labelBackgroundColor=#FFFFFF;"
              f"{'dashed=1;' if punteada else ''}")
    if salida:
        estilo += f"exitX={salida[0]};exitY={salida[1]};exitDx=0;exitDy=0;"
    if entrada:
        estilo += f"entryX={entrada[0]};entryY={entrada[1]};entryDx=0;entryDy=0;"
    geo = '<mxGeometry relative="1" as="geometry">'
    if puntos:
        geo += '<Array as="points">' + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos) + "</Array>"
    geo += "</mxGeometry>"
    celdas.append(f'<mxCell id="{i}" value="{escape(texto)}" style="{estilo}" edge="1" parent="1" source="{a}" target="{b}">{geo}</mxCell>')
    return i


# ---------------- Título ----------------
caja("<b style='font-size:22px'>Analista de datos con IA</b><br>Arquitectura en AWS · us-east-1 · desplegada con Terraform",
     150, 0, 900, 56, "text;html=1;align=left;verticalAlign=middle;fontSize=14;fontColor=#232F3E;")

# ---------------- Grupos (se dibujan primero, quedan al fondo) ----------------
grupo("Nube de AWS", 150, 70, 1640, 1000, "group_aws_cloud_alt", "#232F3E")
grupo("Región us-east-1", 170, 110, 1600, 940, "group_region", "#00A4A6", color_texto="#147EBA", punteado=1)
grupo("VPC 10.20.0.0/16", 640, 160, 760, 760, "group_vpc2", "#8C4FFF", color_texto="#8C4FFF")
recuadro("Zona de disponibilidad A", 665, 205, 345, 690, "#147EBA", "#147EBA")
recuadro("Zona de disponibilidad B", 1030, 205, 345, 690, "#147EBA", "#147EBA")
grupo("Subred pública A", 685, 245, 305, 230, "group_security_group", "#7AA116", "#F2F6E8", "#248814")
grupo("Subred pública B", 1050, 245, 305, 230, "group_security_group", "#7AA116", "#F2F6E8", "#248814")
grupo("Subred privada A · SIN internet", 685, 505, 305, 370, "group_security_group", "#00A4A6", "#E6F6F7", "#147EBA")
grupo("Subred privada B · SIN internet", 1050, 505, 305, 370, "group_security_group", "#00A4A6", "#E6F6F7", "#147EBA")
recuadro("Clúster ECS · Fargate", 745, 285, 560, 390, "#ED7100", "#ED7100")

# ---------------- Usuarios ----------------
usuarios = icono("Usuarios<br>(navegador o celular)", 40, 470, "users", "#232F3E", 64, forma="plain")

# ---------------- Servicios regionales (izquierda) ----------------
s3web = icono("S3<br>Sitio web (chat)", 230, 200, "s3", "#7AA116")
apigw = icono("API Gateway<br>(HTTP API)", 230, 470, "api_gateway", "#E7157B")
lam_arch = icono("Lambda<br>archivos<br>(POST firmado)", 440, 360, "lambda", "#ED7100")
lam_trab = icono("Lambda<br>trabajos<br>(estado y gráficas)", 440, 590, "lambda", "#ED7100")
vpclink = icono("VPC Link", 548, 480, "endpoints", "#8C4FFF", 48, forma="plain")
cloudmap = icono("Cloud Map<br>(nombres internos)", 440, 800, "cloud_map", "#E7157B")
iam = icono("IAM<br>un rol por pieza<br>(mínimo privilegio)", 230, 800, "identity_and_access_management", "#DD344C")

# ---------------- VPC ----------------
igw = icono("Internet<br>gateway", 1000, 136, "internet_gateway", "#8C4FFF", 48, forma="plain")
ag_a = icono("Agente<br>(tarea Fargate)", 810, 330, "fargate", "#ED7100", derecha=True)
ag_b = icono("Agente<br>(autoescala 1–3)", 1175, 330, "fargate", "#ED7100", derecha=True)
sb_a = icono("Sandbox Python<br>(tarea Fargate)", 810, 560, "fargate", "#ED7100", derecha=True)
sb_b = icono("Sandbox Python<br>(autoescala 1–3)", 1175, 560, "fargate", "#ED7100", derecha=True)
ep_ecr = icono("Endpoint<br>ECR", 705, 780, "endpoints", "#8C4FFF", 48, forma="plain")
ep_logs = icono("Endpoint<br>Logs", 800, 780, "endpoints", "#8C4FFF", 48, forma="plain")
ep_s3 = icono("Endpoint S3<br>(gateway, con política)", 1175, 780, "endpoints", "#8C4FFF", 48, forma="plain")

# ---------------- Servicios regionales (derecha) ----------------
bedrock = icono("Amazon Bedrock<br>Claude Haiku 4.5", 1520, 200, "bedrock", "#01A88D")
dynamo = icono("DynamoDB<br>trabajos + conversaciones", 1520, 410, "dynamodb", "#C925D1")
s3datos = icono("S3 datos<br>CSV y gráficas (7 días)", 1520, 610, "s3", "#7AA116")
ecr = icono("ECR<br>imágenes agente/sandbox", 1520, 800, "ecr", "#ED7100")
cw = icono("CloudWatch<br>logs + autoescalado", 1660, 800, "cloudwatch_2", "#E7157B")

# ---------------- Flujos ----------------
flecha(usuarios, s3web, "1. Abre la página", salida=(0.5, 0), entrada=(0, 0.5))
flecha(usuarios, apigw, "2. HTTPS")
flecha(apigw, lam_arch, "POST /archivos", salida=(1, 0.25), entrada=(0, 0.5))
flecha(apigw, vpclink, "POST /preguntas")
flecha(vpclink, ag_a, "", entrada=(0, 0.5))
flecha(apigw, lam_trab, "GET /trabajos/{id}", salida=(1, 0.75), entrada=(0, 0.5))
flecha(lam_arch, s3datos, "3. Sube el CSV (POST firmado ≤10 MB)", punteada=True, salida=(0.5, 0), entrada=(1, 0.5),
       puntos=[(472, 140), (1740, 140), (1740, 642)])
flecha(ag_a, igw, "", salida=(0.5, 0), entrada=(0, 0.5))
flecha(igw, bedrock, "4. Razona y pide herramientas (tool use)", entrada=(0, 0.5))
flecha(ag_a, sb_a, "5. ejecutar_python(código)", salida=(0.5, 1), entrada=(0.5, 0))
flecha(ag_b, dynamo, "6. Pasos + historial (memoria)", salida=(0.5, 0), entrada=(0, 0.5),
       puntos=[(1207, 300), (1460, 300), (1460, 442)])
flecha(sb_b, ep_s3, "", salida=(0.5, 1), entrada=(0.5, 0))
flecha(ep_s3, s3datos, "Lee CSV / guarda PNG", entrada=(0, 0.5))
flecha(lam_trab, dynamo, "7. Consulta el avance", salida=(1, 0.5), entrada=(1, 0.5),
       puntos=[(610, 622), (610, 1035), (1760, 1035), (1760, 442)])
flecha(sb_a, ep_ecr, "", punteada=True, color="#8C4FFF", salida=(0.25, 1), entrada=(0.5, 0))
flecha(sb_a, ep_logs, "", punteada=True, color="#8C4FFF", salida=(0.75, 1), entrada=(0.5, 0))
flecha(ecr, ep_ecr, "Descarga de imágenes", punteada=True, color="#8C4FFF", salida=(0.5, 1), entrada=(0, 0.5),
       puntos=[(1552, 1005), (693, 1005), (693, 804)])

# ---------------- Notas ----------------
nota("<b>Aislamiento del código de la IA</b><br>• Subred privada: sin NAT ni internet gateway<br>• Solo sale a los endpoints de VPC<br>"
     "• Rol IAM: leer datasets/ y escribir resultados/<br>• Subproceso sin credenciales, 30 s máx.<br>"
     "• Riesgo conocido: consultas DNS (sin DNS Firewall)", 560, 1090, 360, 110)
nota("<b>Leyenda</b><br>── flujo de la pregunta<br>- - - archivos e infraestructura<br>"
     "Agente y sandbox: 2 zonas, autoescalado 1–3 tareas", 150, 1090, 360, 90, "#F4F6F8", "#232F3E")

xml = ('<mxfile host="app.diagrams.net"><diagram id="arquitectura" name="Arquitectura">'
       '<mxGraphModel dx="1800" dy="1100" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
       'fold="1" page="1" pageScale="1" pageWidth="1850" pageHeight="1220" math="0" shadow="0"><root>'
       '<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(celdas) + "</root></mxGraphModel></diagram></mxfile>")
(Path(__file__).parent / "arquitectura.drawio").write_text(xml, encoding="utf-8")
print("arquitectura.drawio generado:", len(celdas), "elementos")

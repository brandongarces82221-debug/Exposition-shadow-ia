# VPC propia: subredes públicas (agente, con internet) y privadas (sandbox, sin internet)
locals {
  zonas = ["${var.region}a", "${var.region}b"]
}

resource "aws_vpc" "principal" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.nombre}-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.principal.id
}

resource "aws_subnet" "publica" {
  count                   = 2
  vpc_id                  = aws_vpc.principal.id
  cidr_block              = "10.20.${count.index}.0/24"
  availability_zone       = local.zonas[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.nombre}-publica-${count.index}" }
}

resource "aws_subnet" "privada" {
  count             = 2
  vpc_id            = aws_vpc.principal.id
  cidr_block        = "10.20.${count.index + 10}.0/24"
  availability_zone = local.zonas[count.index]
  tags              = { Name = "${local.nombre}-privada-${count.index}" }
}

resource "aws_route_table" "publica" {
  vpc_id = aws_vpc.principal.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "publica" {
  count          = 2
  subnet_id      = aws_subnet.publica[count.index].id
  route_table_id = aws_route_table.publica.id
}

# Tabla privada SIN ruta a internet: el sandbox solo llega a los endpoints
resource "aws_route_table" "privada" {
  vpc_id = aws_vpc.principal.id
}

resource "aws_route_table_association" "privada" {
  count          = 2
  subnet_id      = aws_subnet.privada[count.index].id
  route_table_id = aws_route_table.privada.id
}

# --- Grupos de seguridad ---
resource "aws_security_group" "vpc_link" {
  name        = "${local.nombre}-vpc-link"
  description = "VPC Link de API Gateway hacia el agente"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_security_group" "agente" {
  name        = "${local.nombre}-agente"
  description = "Agente: recibe del VPC Link, sale a Bedrock/DynamoDB y al sandbox"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_security_group" "sandbox" {
  name        = "${local.nombre}-sandbox"
  description = "Sandbox: solo recibe del agente, solo sale a S3 y endpoints"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_security_group" "endpoints" {
  name        = "${local.nombre}-endpoints"
  description = "Endpoints de interfaz (ECR y CloudWatch Logs)"
  vpc_id      = aws_vpc.principal.id
}

resource "aws_vpc_security_group_egress_rule" "vpc_link_a_agente" {
  security_group_id            = aws_security_group.vpc_link.id
  referenced_security_group_id = aws_security_group.agente.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_ingress_rule" "agente_desde_vpc_link" {
  security_group_id            = aws_security_group.agente.id
  referenced_security_group_id = aws_security_group.vpc_link.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_egress_rule" "agente_https" {
  security_group_id = aws_security_group.agente.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "agente_a_sandbox" {
  security_group_id            = aws_security_group.agente.id
  referenced_security_group_id = aws_security_group.sandbox.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_ingress_rule" "sandbox_desde_agente" {
  security_group_id            = aws_security_group.sandbox.id
  referenced_security_group_id = aws_security_group.agente.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_egress_rule" "sandbox_a_endpoints" {
  security_group_id            = aws_security_group.sandbox.id
  referenced_security_group_id = aws_security_group.endpoints.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

resource "aws_vpc_security_group_egress_rule" "sandbox_a_s3" {
  security_group_id = aws_security_group.sandbox.id
  prefix_list_id    = aws_vpc_endpoint.s3.prefix_list_id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

# El DNS privado de los endpoints aplica a toda la VPC: el agente también descarga de ECR y escribe logs por ellos
resource "aws_vpc_security_group_ingress_rule" "endpoints_desde" {
  for_each                     = { sandbox = aws_security_group.sandbox.id, agente = aws_security_group.agente.id }
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
}

# --- Endpoints ---
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.principal.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.privada.id]
  # Solo el bucket de datos y el bucket donde ECR guarda las capas de las imágenes
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject", "s3:PutObject"]
      Resource = [
        "${aws_s3_bucket.datos.arn}/*",
        "arn:aws:s3:::prod-${var.region}-starport-layer-bucket/*",
      ]
    }]
  })
}

resource "aws_vpc_endpoint" "interfaz" {
  for_each            = toset(["ecr.api", "ecr.dkr", "logs"])
  vpc_id              = aws_vpc.principal.id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [aws_subnet.privada[0].id] # una sola zona para ahorrar
  security_group_ids  = [aws_security_group.endpoints.id]
}

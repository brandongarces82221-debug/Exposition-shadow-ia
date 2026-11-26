resource "aws_apigatewayv2_api" "http" {
  name          = "${local.nombre}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = [local.origen_web]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_stage" "defecto" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    # ~0,7 solicitudes/s por persona con una pregunta en curso: 50/s alcanza para un salón de 30 a la vez
    throttling_rate_limit  = 50
    throttling_burst_limit = 100
  }
}

# --- Lambdas ---
resource "aws_apigatewayv2_integration" "lambda" {
  for_each               = aws_lambda_function.app
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "archivos" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /archivos"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["archivos"].id}"
}

resource "aws_apigatewayv2_route" "trabajos" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /trabajos/{id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["trabajos"].id}"
}

# --- Agente por VPC Link (sin balanceador: Cloud Map con registros SRV) ---
resource "aws_apigatewayv2_vpc_link" "agente" {
  name               = "${local.nombre}-vpc-link"
  subnet_ids         = aws_subnet.publica[*].id
  security_group_ids = [aws_security_group.vpc_link.id]
}

resource "aws_apigatewayv2_integration" "agente" {
  api_id               = aws_apigatewayv2_api.http.id
  integration_type     = "HTTP_PROXY"
  integration_method   = "POST"
  connection_type      = "VPC_LINK"
  connection_id        = aws_apigatewayv2_vpc_link.agente.id
  integration_uri      = aws_service_discovery_service.agente.arn
  timeout_milliseconds = 10000
}

resource "aws_apigatewayv2_route" "preguntas" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /preguntas"
  target    = "integrations/${aws_apigatewayv2_integration.agente.id}"
}

output "url_web" {
  description = "Abre esta dirección en el navegador"
  value       = local.origen_web
}

output "url_api" {
  description = "URL del HTTP API"
  value       = aws_apigatewayv2_stage.defecto.invoke_url
}

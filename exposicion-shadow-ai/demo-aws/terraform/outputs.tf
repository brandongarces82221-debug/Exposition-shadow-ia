output "url" {
  description = "Abre esta URL (tarda ~2 minutos en estar lista tras el apply)"
  value       = "http://${aws_instance.demo.public_ip}"
}

output "guardrail_id" {
  value = aws_bedrock_guardrail.demo.guardrail_id
}

output "instance_id" {
  value = aws_instance.demo.id
}

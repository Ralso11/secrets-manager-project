output "api_url" {
  description = "Base URL of the secret-checking API"
  value       = "${aws_apigatewayv2_stage.default.invoke_url}secret-check"
}

output "secret_name" {
  description = "Name of the secret in Secrets Manager"
  value       = aws_secretsmanager_secret.app_secret.name
}

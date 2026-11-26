data "archive_file" "lambda" {
  for_each    = toset(["archivos", "trabajos"])
  type        = "zip"
  source_file = "${path.module}/../app/lambdas/${each.key}.py"
  output_path = "${path.module}/.construccion/${each.key}.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = data.archive_file.lambda
  name              = "/aws/lambda/${local.nombre}-${each.key}"
  retention_in_days = 7
}

resource "aws_lambda_function" "app" {
  for_each         = data.archive_file.lambda
  function_name    = "${local.nombre}-${each.key}"
  role             = aws_iam_role.lambda[each.key].arn
  runtime          = "python3.12"
  handler          = "${each.key}.handler"
  filename         = each.value.output_path
  source_code_hash = each.value.output_base64sha256
  timeout          = 10
  memory_size      = 256
  environment {
    variables = {
      BUCKET_DATOS   = aws_s3_bucket.datos.bucket
      TABLA_TRABAJOS = aws_dynamodb_table.trabajos.name
    }
  }
  depends_on = [aws_cloudwatch_log_group.lambda]
}

resource "aws_lambda_permission" "api" {
  for_each      = aws_lambda_function.app
  function_name = each.value.function_name
  action        = "lambda:InvokeFunction"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

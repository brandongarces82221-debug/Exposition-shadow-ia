data "aws_iam_policy_document" "asumir_ecs" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "asumir_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- Rol de ejecución (lo usa ECS para descargar la imagen y escribir logs) ---
resource "aws_iam_role" "ejecucion" {
  name               = "${local.nombre}-ecs-ejecucion"
  assume_role_policy = data.aws_iam_policy_document.asumir_ecs.json
}

resource "aws_iam_role_policy_attachment" "ejecucion" {
  role       = aws_iam_role.ejecucion.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# --- Rol del agente: Bedrock (solo Haiku 4.5) y las dos tablas ---
resource "aws_iam_role" "agente" {
  name               = "${local.nombre}-agente"
  assume_role_policy = data.aws_iam_policy_document.asumir_ecs.json
}

resource "aws_iam_role_policy" "agente" {
  role = aws_iam_role.agente.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:${var.region}:${local.cuenta}:inference-profile/${var.model_id}",
          # El perfil global enruta a cualquier región: se permite el modelo base en todas
          "arn:aws:bedrock:*::foundation-model/${var.modelo_base}",
          "arn:aws:bedrock:::foundation-model/${var.modelo_base}",
        ]
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
        Resource = [aws_dynamodb_table.trabajos.arn, aws_dynamodb_table.conversaciones.arn]
      },
    ]
  })
}

# --- Rol del sandbox: leer CSV y guardar gráficas, nada más ---
resource "aws_iam_role" "sandbox" {
  name               = "${local.nombre}-sandbox"
  assume_role_policy = data.aws_iam_policy_document.asumir_ecs.json
}

resource "aws_iam_role_policy" "sandbox" {
  role = aws_iam_role.sandbox.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.datos.arn}/datasets/*" },
      { Effect = "Allow", Action = "s3:PutObject", Resource = "${aws_s3_bucket.datos.arn}/resultados/*" },
    ]
  })
}

# --- Roles de las Lambdas ---
resource "aws_iam_role" "lambda" {
  for_each           = toset(["archivos", "trabajos"])
  name               = "${local.nombre}-lambda-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.asumir_lambda.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  for_each   = aws_iam_role.lambda
  role       = each.value.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# La firma del POST usa los permisos de la Lambda: solo puede autorizar subidas a datasets/
resource "aws_iam_role_policy" "lambda_archivos" {
  role = aws_iam_role.lambda["archivos"].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "s3:PutObject", Resource = "${aws_s3_bucket.datos.arn}/datasets/*" }]
  })
}

resource "aws_iam_role_policy" "lambda_trabajos" {
  role = aws_iam_role.lambda["trabajos"].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = "dynamodb:GetItem", Resource = aws_dynamodb_table.trabajos.arn },
      { Effect = "Allow", Action = "s3:GetObject", Resource = "${aws_s3_bucket.datos.arn}/resultados/*" },
    ]
  })
}

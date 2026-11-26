# --- Bucket del sitio web (público, solo lectura) ---
resource "aws_s3_bucket" "web" {
  bucket        = "${local.nombre}-web-${local.cuenta}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "web" {
  bucket = aws_s3_bucket.web.id
  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket     = aws_s3_bucket.web.id
  depends_on = [aws_s3_bucket_public_access_block.web]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.web.arn}/*"
    }]
  })
}

# --- Bucket de datos (privado): CSV subidos y gráficas ---
resource "aws_s3_bucket" "datos" {
  bucket        = "${local.nombre}-datos-${local.cuenta}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "datos" {
  bucket                  = aws_s3_bucket.datos.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  rule {
    id     = "borrar-a-los-7-dias"
    status = "Enabled"
    filter {}
    expiration {
      days = 7
    }
  }
}

# El navegador sube el CSV directo al bucket con un POST firmado
resource "aws_s3_bucket_cors_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  cors_rule {
    allowed_methods = ["POST"]
    allowed_origins = [local.origen_web]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

# --- DynamoDB ---
resource "aws_dynamodb_table" "trabajos" {
  name         = "${local.nombre}-trabajos"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "trabajo_id"
  attribute {
    name = "trabajo_id"
    type = "S"
  }
  ttl {
    attribute_name = "expira"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "conversaciones" {
  name         = "${local.nombre}-conversaciones"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "conversacion"
  range_key    = "turno"
  attribute {
    name = "conversacion"
    type = "S"
  }
  attribute {
    name = "turno"
    type = "N"
  }
  ttl {
    attribute_name = "expira"
    enabled        = true
  }
}

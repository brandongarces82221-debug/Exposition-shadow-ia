locals {
  origen_web = "http://${aws_s3_bucket_website_configuration.web.website_endpoint}"
  dir_web    = "${path.module}/../web"
  tipos = {
    html = "text/html; charset=utf-8"
    css  = "text/css; charset=utf-8"
    js   = "application/javascript; charset=utf-8"
  }
  archivos_web = [for f in fileset(local.dir_web, "*") : f if f != "config.js"]
}

resource "aws_s3_object" "web" {
  for_each      = toset(local.archivos_web)
  bucket        = aws_s3_bucket.web.id
  key           = each.value
  source        = "${local.dir_web}/${each.value}"
  etag          = filemd5("${local.dir_web}/${each.value}")
  content_type  = lookup(local.tipos, reverse(split(".", each.value))[0], "application/octet-stream")
  cache_control = "no-cache"
}

# La página lee aquí la URL de la API
resource "aws_s3_object" "config" {
  bucket        = aws_s3_bucket.web.id
  key           = "config.js"
  content       = "window.CONFIG = { api: \"${aws_apigatewayv2_stage.defecto.invoke_url}\" };\n"
  content_type  = local.tipos.js
  cache_control = "no-cache"
}

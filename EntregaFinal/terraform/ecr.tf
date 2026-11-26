locals {
  apps = {
    agente  = "${path.module}/../app/agente"
    sandbox = "${path.module}/../app/sandbox"
  }
  # Si cambia cualquier archivo de la app (sin contar pruebas), se reconstruye la imagen
  hash_app = {
    for nombre, ruta in local.apps : nombre => sha1(join("", [
      for f in sort(fileset(ruta, "**")) : filesha1("${ruta}/${f}")
      if !startswith(basename(f), "test_") && basename(f) != "conftest.py" && !strcontains(f, "__pycache__")
    ]))
  }
}

resource "aws_ecr_repository" "app" {
  for_each     = local.apps
  name         = "${local.nombre}-${each.key}"
  force_delete = true
}

resource "docker_image" "app" {
  for_each = local.apps
  name     = "${aws_ecr_repository.app[each.key].repository_url}:${substr(local.hash_app[each.key], 0, 12)}"
  build {
    context  = each.value
    platform = "linux/amd64"
  }
  triggers = { hash = local.hash_app[each.key] }
}

resource "docker_registry_image" "app" {
  for_each      = local.apps
  name          = docker_image.app[each.key].name
  keep_remotely = true
  triggers      = { hash = local.hash_app[each.key] }
}

resource "aws_ecs_cluster" "principal" {
  name = "${local.nombre}-cluster"
}

resource "aws_cloudwatch_log_group" "app" {
  for_each          = toset(["agente", "sandbox"])
  name              = "/ecs/${local.nombre}-${each.key}"
  retention_in_days = 7
}

# --- Cloud Map: nombres privados para encontrar las tareas ---
resource "aws_service_discovery_private_dns_namespace" "interno" {
  name = "analista.local"
  vpc  = aws_vpc.principal.id
}

# El VPC Link de un HTTP API necesita registros SRV (IP + puerto)
resource "aws_service_discovery_service" "agente" {
  name = "agente"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.interno.id
    routing_policy = "MULTIVALUE"
    dns_records {
      type = "SRV"
      ttl  = 10
    }
  }
}

resource "aws_service_discovery_service" "sandbox" {
  name = "sandbox"
  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.interno.id
    routing_policy = "MULTIVALUE"
    dns_records {
      type = "A"
      ttl  = 10
    }
  }
}

locals {
  imagen = { for k, _ in local.apps : k => "${aws_ecr_repository.app[k].repository_url}@${docker_registry_image.app[k].sha256_digest}" }
  logs = { for k in ["agente", "sandbox"] : k => {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.app[k].name
      "awslogs-region"        = var.region
      "awslogs-stream-prefix" = k
    }
  } }
}

# --- Agente: 0.25 vCPU / 0.5 GB, subred pública con IP pública (sale a Bedrock sin NAT) ---
resource "aws_ecs_task_definition" "agente" {
  family                   = "${local.nombre}-agente"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ejecucion.arn
  task_role_arn            = aws_iam_role.agente.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name         = "agente"
    image        = local.imagen["agente"]
    essential    = true
    portMappings = [{ containerPort = 8080, protocol = "tcp" }]
    environment = [
      { name = "TABLA_TRABAJOS", value = aws_dynamodb_table.trabajos.name },
      { name = "TABLA_CONVERSACIONES", value = aws_dynamodb_table.conversaciones.name },
      { name = "URL_SANDBOX", value = "http://sandbox.analista.local:8080" },
      { name = "MODEL_ID", value = var.model_id },
      { name = "AWS_REGION", value = var.region },
    ]
    logConfiguration = local.logs["agente"]
  }])
}

resource "aws_ecs_service" "agente" {
  name            = "${local.nombre}-agente"
  cluster         = aws_ecs_cluster.principal.id
  task_definition = aws_ecs_task_definition.agente.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.publica[*].id
    security_groups  = [aws_security_group.agente.id]
    assign_public_ip = true
  }
  service_registries {
    registry_arn   = aws_service_discovery_service.agente.arn
    container_name = "agente"
    container_port = 8080
  }
  lifecycle {
    ignore_changes = [desired_count] # lo maneja el autoescalado
  }
}

# --- Sandbox: 0.5 vCPU / 1 GB, subred privada sin internet, raíz de solo lectura ---
resource "aws_ecs_task_definition" "sandbox" {
  family                   = "${local.nombre}-sandbox"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ejecucion.arn
  task_role_arn            = aws_iam_role.sandbox.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  volume {
    name = "tmp"
  }
  container_definitions = jsonencode([{
    name                   = "sandbox"
    image                  = local.imagen["sandbox"]
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 8080, protocol = "tcp" }]
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp" }]
    environment = [
      { name = "BUCKET_DATOS", value = aws_s3_bucket.datos.bucket },
      { name = "AWS_REGION", value = var.region },
    ]
    logConfiguration = local.logs["sandbox"]
  }])
}

resource "aws_ecs_service" "sandbox" {
  name            = "${local.nombre}-sandbox"
  cluster         = aws_ecs_cluster.principal.id
  task_definition = aws_ecs_task_definition.sandbox.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = aws_subnet.privada[*].id
    security_groups  = [aws_security_group.sandbox.id]
    assign_public_ip = false
  }
  service_registries {
    registry_arn = aws_service_discovery_service.sandbox.arn
  }
  depends_on = [aws_vpc_endpoint.interfaz, aws_vpc_endpoint.s3]
  lifecycle {
    ignore_changes = [desired_count]
  }
}

# --- Autoescalado: 1 a 3 tareas por servicio según CPU (60 %) ---
resource "aws_appautoscaling_target" "servicio" {
  for_each           = { agente = aws_ecs_service.agente.name, sandbox = aws_ecs_service.sandbox.name }
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.principal.name}/${each.value}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 1
  max_capacity       = var.tareas_max
}

resource "aws_appautoscaling_policy" "cpu" {
  for_each           = aws_appautoscaling_target.servicio
  name               = "${local.nombre}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = each.value.service_namespace
  resource_id        = each.value.resource_id
  scalable_dimension = each.value.scalable_dimension
  target_tracking_scaling_policy_configuration {
    target_value = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.0" }
    docker  = { source = "kreuzwerker/docker", version = "~> 3.6" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
  # Estado local en el Codespace (no se sube al repo). Ver README: "si borras el Codespace antes de destroy".
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Proyecto = "analista-datos" }
  }
}

data "aws_caller_identity" "yo" {}
data "aws_ecr_authorization_token" "ecr" {}

locals {
  cuenta   = data.aws_caller_identity.yo.account_id
  registro = "${local.cuenta}.dkr.ecr.${var.region}.amazonaws.com"
  nombre   = var.prefijo
}

# Construye las imágenes con el Docker del Codespace y las sube a ECR durante el apply
provider "docker" {
  registry_auth {
    address  = local.registro
    username = data.aws_ecr_authorization_token.ecr.user_name
    password = data.aws_ecr_authorization_token.ecr.password
  }
}

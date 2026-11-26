variable "region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Tamaño de la máquina (t3.micro entra en la capa gratuita)"
  type        = string
  default     = "t3.micro"
}

variable "model_id" {
  description = "Modelo de Claude en Bedrock (Haiku es el más barato)"
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "secret_code" {
  description = "El código que el curso intenta robar"
  type        = string
  default     = "DRAGON-7731"
}

variable "allowed_cidr" {
  description = "Quién puede abrir la página. 0.0.0.0/0 = cualquiera (necesario si el curso entra desde sus celulares)"
  type        = string
  default     = "0.0.0.0/0"
}

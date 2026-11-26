variable "region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "prefijo" {
  description = "Prefijo para los nombres de los recursos"
  type        = string
  default     = "analista"
}

variable "model_id" {
  description = "Perfil de inferencia de Bedrock que usa el agente"
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "modelo_base" {
  description = "Modelo base detrás del perfil de inferencia (para el permiso IAM)"
  type        = string
  default     = "anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "tareas_max" {
  description = "Máximo de tareas por servicio con autoescalado"
  type        = number
  default     = 3
}

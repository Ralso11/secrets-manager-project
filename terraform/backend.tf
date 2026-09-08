terraform {
  backend "s3" {
    bucket = "ralso11-terraform-state-2026"
    key    = "secrets-manager-project/terraform.tfstate"
    region = "eu-central-1"
  }
}

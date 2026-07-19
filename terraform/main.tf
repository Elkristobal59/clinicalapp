terraform {
  required_providers {
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.21.0"
    }
  }
}

# Configuration du provider pour se connecter à Supabase via l'URL Postgres
provider "postgresql" {
  # La variable contient l'URL au format: postgresql://postgres.user:password@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
  # Le provider va la parser automatiquement. On utilise l'attribut sslmode=require en production.
  connect_string = "${var.supabase_db_url}?sslmode=require"
}

# 1. Activation de l'extension vector sur Supabase
resource "postgresql_extension" "pgvector" {
  name = "vector"
}

# 2. Exécution du script SQL de structure de base de données
# Le provider terraform postgresql n'a pas de ressource native pour les colonnes de type `vector(768)`
# et pour les index HNSW. La meilleure pratique est d'utiliser `postgresql_function` 
# ou `null_resource` avec un provisioner pour jouer un script SQL pur.

# Toutefois, pour la simplicité, on utilise un outil tiers ou une migration. 
# Ici on exécute une null_resource qui se connecte via psql.
# Une alternative pure Terraform est de créer un rôle ou schéma, mais pour une table
# spécifique, le SQL est roi.

# Par sécurité, ce block demande la présence du client PostgreSQL (psql) sur la machine qui lance Terraform.
resource "null_resource" "supabase_schema" {
  triggers = {
    # Relancer si le script schema.sql change
    schema_sha1 = sha1(file("${path.module}/schema.sql"))
  }

  provisioner "local-exec" {
    # On joue le script SQL directement sur la base Supabase.
    command = "psql \"${var.supabase_db_url}\" -f ${path.module}/schema.sql"
  }

  depends_on = [
    postgresql_extension.pgvector
  ]
}

output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Frontend bucket URL"
  value       = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

output "docker_registry" {
  description = "Artifact Registry URL for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "db_instance_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

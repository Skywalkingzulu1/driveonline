#!/usr/bin/env bash

# Blue-Green deployment script for AWS ECS
# This script registers a new task definition with the provided image,
# updates the ECS service to use the new task definition, and waits for
# the service to become stable before confirming the promotion.

set -euo pipefail

# Required environment variables:
#   CLUSTER_NAME   - Name of the ECS cluster
#   SERVICE_NAME   - Name of the ECS service to update
#   IMAGE_URI      - Full URI of the new Docker image (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/driveonline:latest)
#   AWS_REGION     - AWS region (optional, defaults to us-east-1)

: "${CLUSTER_NAME:?Need to set CLUSTER_NAME}"
: "${SERVICE_NAME:?Need to set SERVICE_NAME}"
: "${IMAGE_URI:?Need to set IMAGE_URI}"
AWS_REGION=${AWS_REGION:-us-east-1}

# Helper function for logging
log() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] $*"
}

log "Starting blue‑green deployment for service '$SERVICE_NAME' in cluster '$CLUSTER_NAME'"

# 1. Retrieve the current task definition ARN used by the service
CURRENT_TASK_DEF_ARN=$(aws ecs describe-services \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --region "$AWS_REGION" \
  --query "services[0].taskDefinition" \
  --output text)

log "Current task definition ARN: $CURRENT_TASK_DEF_ARN"

# 2. Get the full task definition JSON
CURRENT_TASK_DEF_JSON=$(aws ecs describe-task-definition \
  --task-definition "$CURRENT_TASK_DEF_ARN" \
  --region "$AWS_REGION" \
  --query "taskDefinition" \
  --output json)

# 3. Update the container image in the task definition JSON (assumes a single container)
NEW_TASK_DEF_JSON=$(echo "$CURRENT_TASK_DEF_JSON" | jq --arg img "$IMAGE_URI" \
  '.containerDefinitions[0].image = $img')

# Preserve required top‑level fields for registration (remove read‑only fields)
REGISTER_PAYLOAD=$(echo "$NEW_TASK_DEF_JSON" | jq '{
  family: .family,
  taskRoleArn: .taskRoleArn,
  executionRoleArn: .executionRoleArn,
  networkMode: .networkMode,
  containerDefinitions: .containerDefinitions,
  volumes: .volumes,
  placementConstraints: .placementConstraints,
  requiresCompatibilities: .requiresCompatibilities,
  cpu: .cpu,
  memory: .memory,
  tags: .tags
}')

log "Registering new task definition with updated image..."
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json "$REGISTER_PAYLOAD" \
  --region "$AWS_REGION" \
  --query "taskDefinition.taskDefinitionArn" \
  --output text)

log "New task definition ARN: $NEW_TASK_DEF_ARN"

# 4. Update the ECS service to use the new task definition
log "Updating service to use the new task definition..."
aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --task-definition "$NEW_TASK_DEF_ARN" \
  --region "$AWS_REGION" \
  --force-new-deployment

# 5. Wait for the service to become stable (all tasks pass health checks)
log "Waiting for service to reach a stable state..."
aws ecs wait services-stable \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --region "$AWS_REGION"

log "Blue‑green deployment completed successfully. Service is now running the new image."

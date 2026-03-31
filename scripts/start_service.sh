#!/usr/bin/env bash
set -e

echo "=== ApplicationStart Hook ==="
echo "Registering new ECS task definition..."

# Register the task definition and capture its ARN
TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json
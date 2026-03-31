#!/usr/bin/env bash
set -e

echo "=== ValidateService Hook ==="
CLUSTER_NAME="<ecs-cluster-name>"
SERVICE_NAME="<ecs-service-name>"

echo "Polling deployment status..."
MAX_ATTEMPTS=20
SLEEP_SECONDS=15

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  STATUS=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --query 'services[0].deployments[?status==`PRIMARY`].status' \
    --output text)

  if [[ "$STATUS" == "PRIMARY" ]]; then
    echo "Deployment successful – service is in PRIMARY state."
    exit 0
  else
    echo "Attempt $i/$MAX_ATTEMPTS: Service not ready yet. Waiting $SLEEP_SECONDS seconds..."
    sleep $SLEEP_SECONDS
  fi
done

echo "ERROR: Service failed to reach PRIMARY state within the expected time."
exit 1
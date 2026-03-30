#!/usr/bin/env bash
# =============================================================================
# Script: set_github_secrets.sh
# Purpose: Store AWS credentials as encrypted secrets in a GitHub repository.
# Requirements:
#   - GitHub CLI (gh) must be installed and authenticated.
#   - The user must have write permissions to the target repository.
# Usage:
#   ./set_github_secrets.sh <owner/repo> <AWS_ACCESS_KEY_ID> <AWS_SECRET_ACCESS_KEY>
# Example:
#   ./set_github_secrets.sh Skywalkingzulu1/driveonline AKIA... abcdef...
# =============================================================================

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Error: Incorrect number of arguments."
    echo "Usage: $0 <owner/repo> <AWS_ACCESS_KEY_ID> <AWS_SECRET_ACCESS_KEY>"
    exit 1
fi

REPO="$1"
AWS_KEY_ID="$2"
AWS_SECRET_KEY="$3"

echo "Setting AWS_ACCESS_KEY_ID secret for repository $REPO..."
echo -n "$AWS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID -b- -R "$REPO"

echo "Setting AWS_SECRET_ACCESS_KEY secret for repository $REPO..."
echo -n "$AWS_SECRET_KEY" | gh secret set AWS_SECRET_ACCESS_KEY -b- -R "$REPO"

echo "✅ AWS credentials have been stored as encrypted secrets in $REPO."
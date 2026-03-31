#!/usr/bin/env python3
"""
Blue‑Green deployment helper for an existing Amazon ECS service.

This script:
1. Registers a new task set (the "green" version) using a supplied task definition.
2. Gradually shifts traffic from the current task set (the "blue" version) to the new one.
3. Rolls back to the original task set if any step fails.

Prerequisites
-------------
- AWS credentials configured (via environment variables, shared config, or IAM role).
- The target ECS service must be fronted by an Application Load Balancer (ALB) with
  at least one listener rule that uses the `targetGroupArn` of the task set.
- boto3 must be installed (included in requirements.txt).

Usage
-----
    python deploy_blue_green.py \\
        --cluster my-cluster \\
        --service my-service \\
        --task-def arn:aws:ecs:region:account-id:task-definition/my-task-def:2 \\
        --desired-count 2 \\
        [--step 0.1] [--wait 30]

Arguments
---------
- ``--cluster``          : Name or ARN of the ECS cluster.
- ``--service``          : Name of the ECS service to update.
- ``--task-def``         : ARN of the new task definition to deploy.
- ``--desired-count``    : Desired number of tasks for the new task set.
- ``--step`` (optional) : Traffic shift increment (default 0.1 = 10%).
- ``--wait`` (optional) : Seconds to wait between shift steps (default 30).
"""

import argparse
import os
import sys
import time
import logging
from typing import List, Dict

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ecs = boto3.client("ecs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blue‑Green deployment for ECS")
    parser.add_argument("--cluster", required=True, help="ECS cluster name or ARN")
    parser.add_argument("--service", required=True, help="ECS service name")
    parser.add_argument("--task-def", required=True, help="New task definition ARN")
    parser.add_argument(
        "--desired-count",
        type=int,
        required=True,
        help="Desired number of tasks for the new task set",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.1,
        help="Traffic shift increment (0 < step <= 1). Default 0.1",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=30,
        help="Seconds to wait between traffic shift steps. Default 30",
    )
    return parser.parse_args()


def get_service(cluster: str, service: str) -> Dict:
    """Retrieve the service description."""
    resp = ecs.describe_services(cluster=cluster, services=[service])
    services = resp.get("services", [])
    if not services:
        raise RuntimeError(f"Service {service} not found in cluster {cluster}")
    return services[0]


def list_task_sets(cluster: str, service: str) -> List[Dict]:
    """List all task sets for a service."""
    paginator = ecs.get_paginator("list_task_sets")
    task_sets = []
    for page in paginator.paginate(cluster=cluster, service=service):
        task_sets.extend(page.get("taskSets", []))
    return task_sets


def create_task_set(
    cluster: str,
    service: str,
    task_definition: str,
    desired_count: int,
) -> Dict:
    """Create a new task set (green) with zero traffic."""
    service_desc = get_service(cluster, service)

    # Extract required fields from the existing service for compatibility
    launch_type = service_desc.get("launchType")
    network_configuration = service_desc.get("networkConfiguration")
    load_balancers = service_desc.get("loadBalancers", [])
    platform_version = service_desc.get("platformVersion")
    capacity_provider_strategy = service_desc.get("capacityProviderStrategy")
    deployment_controller = service_desc.get("deploymentController", {})

    params = {
        "service": service,
        "cluster": cluster,
        "taskDefinition": task_definition,
        "scale": {"value": 0.0, "unit": "PERCENT"},
        "desiredCount": desired_count,
    }

    if launch_type:
        params["launchType"] = launch_type
    if network_configuration:
        params["networkConfiguration"] = network_configuration
    if load_balancers:
        params["loadBalancers"] = load_balancers
    if platform_version:
        params["platformVersion"] = platform_version
    if capacity_provider_strategy:
        params["capacityProviderStrategy"] = capacity_provider_strategy
    if deployment_controller:
        params["deploymentController"] = deployment_controller

    try:
        resp = ecs.create_task_set(**params)
        task_set = resp["taskSet"]
        log.info(
            f"Created new task set {task_set['taskSetArn']} with desired count {desired_count}"
        )
        return task_set
    except ClientError as e:
        raise RuntimeError(f"Failed to create task set: {e}")


def update_task_set_scale(
    cluster: str, service: str, task_set_arn: str, scale: float
) -> None:
    """Update the traffic weight (scale) of a task set."""
    try:
        ecs.update_task_set(
            cluster=cluster,
            service=service,
            taskSet=task_set_arn,
            scale={"value": scale, "unit": "PERCENT"},
        )
        log.info(f"Set scale of {task_set_arn} to {scale * 100:.1f}%")
    except ClientError as e:
        raise RuntimeError(f"Failed to update scale for {task_set_arn}: {e}")


def wait_for_stable_task_set(
    cluster: str, service: str, task_set_arn: str, timeout: int = 600
) -> None:
    """Wait until the task set reaches a stable state (RUNNING)."""
    start = time.time()
    while True:
        resp = ecs.describe_task_sets(
            cluster=cluster, service=service, taskSets=[task_set_arn]
        )
        task_set = resp["taskSets"][0]
        status = task_set.get("status")
        if status == "PRIMARY" or status == "ACTIVE":
            # ACTIVE means it's ready but not primary yet
            break
        if time.time() - start > timeout:
            raise RuntimeError(f"Task set {task_set_arn} did not become stable in time")
        log.debug(f"Waiting for task set {task_set_arn} to become stable (status={status})")
        time.sleep(5)


def perform_traffic_shift(
    cluster: str,
    service: str,
    old_task_set_arn: str,
    new_task_set_arn: str,
    step: float,
    wait_seconds: int,
) -> None:
    """Gradually shift traffic from old to new task set."""
    old_scale = 1.0
    new_scale = 0.0

    while new_scale < 1.0:
        new_scale = min(new_scale + step, 1.0)
        old_scale = max(1.0 - new_scale, 0.0)

        update_task_set_scale(cluster, service, new_task_set_arn, new_scale)
        update_task_set_scale(cluster, service, old_task_set_arn, old_scale)

        # Give ECS a moment to propagate the changes
        time.sleep(wait_seconds)

    log.info("Traffic shift complete. New task set now receives 100% traffic.")


def set_primary_task_set(cluster: str, service: str, task_set_arn: str) -> None:
    """Mark the given task set as PRIMARY."""
    try:
        ecs.update_task_set(
            cluster=cluster,
            service=service,
            taskSet=task_set_arn,
            primary=True,
        )
        log.info(f"Task set {task_set_arn} marked as PRIMARY")
    except ClientError as e:
        raise RuntimeError(f"Failed to set primary task set: {e}")


def delete_task_set(cluster: str, service: str, task_set_arn: str) -> None:
    """Delete a task set (used for rollback or cleanup)."""
    try:
        ecs.delete_task_set(cluster=cluster, service=service, taskSet=task_set_arn)
        log.info(f"Deleted task set {task_set_arn}")
    except ClientError as e:
        raise RuntimeError(f"Failed to delete task set {task_set_arn}: {e}")


def main() -> None:
    args = parse_args()

    # Validate step
    if not (0 < args.step <= 1):
        log.error("--step must be between 0 (exclusive) and 1 (inclusive)")
        sys.exit(1)

    # 1️⃣ Create the new (green) task set
    try:
        new_task_set = create_task_set(
            cluster=args.cluster,
            service=args.service,
            task_definition=args.task_def,
            desired_count=args.desired_count,
        )
    except RuntimeError as e:
        log.error(e)
        sys.exit(1)

    new_arn = new_task_set["taskSetArn"]

    # 2️⃣ Identify the current (blue) task set – the one with PRIMARY status
    try:
        task_sets = list_task_sets(args.cluster, args.service)
        old_task_set = next(
            (ts for ts in task_sets if ts.get("status") == "PRIMARY"), None
        )
        if not old_task_set:
            raise RuntimeError("No PRIMARY task set found; cannot perform blue‑green")
        old_arn = old_task_set["taskSetArn"]
    except RuntimeError as e:
        log.error(e)
        # Cleanup the newly created task set before exiting
        delete_task_set(args.cluster, args.service, new_arn)
        sys.exit(1)

    # 3️⃣ Wait for the new task set to be ACTIVE (tasks started)
    try:
        wait_for_stable_task_set(args.cluster, args.service, new_arn)
    except RuntimeError as e:
        log.error(e)
        # Rollback: delete new task set
        delete_task_set(args.cluster, args.service, new_arn)
        sys.exit(1)

    # 4️⃣ Gradually shift traffic
    try:
        perform_traffic_shift(
            args.cluster,
            args.service,
            old_task_set_arn=old_arn,
            new_task_set_arn=new_arn,
            step=args.step,
            wait_seconds=args.wait,
        )
    except RuntimeError as e:
        log.error(f"Traffic shift failed: {e}")
        # Rollback: restore old task set to 100% and delete new
        update_task_set_scale(args.cluster, args.service, old_arn, 1.0)
        update_task_set_scale(args.cluster, args.service, new_arn, 0.0)
        delete_task_set(args.cluster, args.service, new_arn)
        sys.exit(1)

    # 5️⃣ Promote new task set to PRIMARY
    try:
        set_primary_task_set(args.cluster, args.service, new_arn)
    except RuntimeError as e:
        log.error(f"Failed to promote new task set: {e}")
        # Attempt rollback again
        update_task_set_scale(args.cluster, args.service, old_arn, 1.0)
        update_task_set_scale(args.cluster, args.service, new_arn, 0.0)
        delete_task_set(args.cluster, args.service, new_arn)
        sys.exit(1)

    # 6️⃣ Cleanup old task set (optional – can be kept for manual rollback)
    try:
        delete_task_set(args.cluster, args.service, old_arn)
    except RuntimeError as e:
        log.warning(f"Could not delete old task set {old_arn}: {e}")

    log.info("Blue‑green deployment completed successfully.")


if __name__ == "__main__":
    main()
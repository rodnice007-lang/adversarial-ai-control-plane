#!/bin/bash

echo "Starting Adversarial AI Control Plane..."

echo "Running test harness locally..."

python control_plane/mission_start.py

echo "Checking Docker..."

if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Skipping container execution."
    exit 0
fi

echo "Building Docker image..."

docker build -t ai-control-plane:v3.5 -f infra/Dockerfile .

echo "Running container..."

docker run --rm ai-control-plane:v3.5

echo "Process complete."


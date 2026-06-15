#!/bin/bash

echo "Starting Adversarial AI Control Plane..."

echo "Running test harness locally..."
python control_plane_v3_5/test_harness.py

echo "Building Docker image..."
docker build -t ai-control-plane:v3.5 -f control_plane_v3_5/Dockerfile .

echo "Running container..."
docker run --rm ai-control-plane:v3.5

echo "Process complete."


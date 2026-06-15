# Adversarial AI Control Plane v3.5

## Overview
This project simulates a stateful AI security control plane.

It intercepts requests, evaluates behavior, assigns risk, and enforces decisions before passing data to downstream systems.

## Core Features
- Stateful request tracking
- Risk scoring (0–100)
- Role-based access control (RBAC)
- MFA enforcement
- 4-state decision system

## Decision States
- REJECT → block malicious requests
- ISOLATE → restrict suspicious activity
- ENFORCE → apply policy controls
- ALLOW → permit valid access

## Project Structure

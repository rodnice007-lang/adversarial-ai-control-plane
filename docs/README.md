# Adversarial AI Control Plane

## Overview

The Adversarial AI Control Plane is a programmable governance, security, and orchestration layer designed to sit between users, applications, and AI inference engines.

Inspired by Software-Defined Networking (SDN) principles, the platform separates policy enforcement and security evaluation from model execution. Rather than relying on an AI model to evaluate its own behavior, the control plane performs independent inspection, validation, policy enforcement, routing, logging, and auditing before requests reach downstream models or services.

The project explores how security controls can be applied to AI systems using deterministic policies, transparent decision-making, and infrastructure automation.

**Security decisions occur outside the model, not inside it.**

## Homelab & Development Environment

This project is developed and tested in a dual-node homelab environment designed to support cybersecurity, AI governance, infrastructure automation, and cloud learning.

### Development Workstation

**MSI Vector 16 HX**

- Windows 11
- WSL2 Ubuntu
- VS Code
- Git
- Terraform
- Azure CLI
- Kali Linux VM
- Wireshark
- Packet Tracer

### Infrastructure Node

**MINISFORUM AI X1 Pro-470**

- Windows 11
- WSL2 Ubuntu
- Docker
- Control Plane Services
- Automation Workloads
- Persistent Infrastructure

### Storage Layer

**Samsung T7 2TB**

- ISO repository
- Backup archives
- Lab exports
- Documentation

### Cloud Layer

**Microsoft Azure**

- Terraform-managed resources
- AZ-104 learning environment
- Identity and governance experiments
- Hybrid cloud testing

## Security Architecture

### Control Plane Flow

```
User -> Control Plane -> AI -> Control Plane -> Output
```

### Processing Pipeline

```
Loop -> Validate -> Classify -> Risk Fusion -> Enforce -> Log
```

The runtime control plane implements the enforcement path while the canonical architecture defines how decisions are computed through:

- Tier 1 Hard Controls
- Tier 2 Behavioral Analysis
- Risk Fusion Engine
- Enforcement State Mapping

### Core Features

- Stateful request tracking
- Risk scoring (0-100)
- Role-Based Access Control (RBAC)
- MFA enforcement
- Input validation and normalization
- Regex attack detection
- Canary token protection
- Output monitoring and DLP inspection
- Quarantine workflows
- Structured audit logging
- Async processing pipeline
- Docker-based local deployment
- Azure cloud deployment support

### Decision States

| State | Action |
|---|---|
| REJECT | Block |
| ISOLATE | Quarantine |
| ENFORCE | Policy-Guarded Model Execution |
| ALLOW | Permit |

### Enforcement Philosophy

- REJECT blocks confirmed malicious behavior.
- ISOLATE routes suspicious activity to quarantine.
- ENFORCE allows execution under additional policy restrictions and monitoring.
- ALLOW permits normal execution.

## Production Hardening (v3.5 Enhanced)

### Operational Reliability

**Async Task Tracking**
- Tracks background task lifecycle using `self.tasks`
- Prevents orphaned asynchronous jobs
- Enables controlled shutdown procedures

**Graceful Shutdown Handling**
- Waits for active tasks to complete
- Prevents loss of in-flight events
- Improves operational reliability

### Security & Audit Hardening

**Structured Logging**

Severity-based logging:
- LOW
- MEDIUM
- HIGH
- CRITICAL

Supports SIEM ingestion, enables alert prioritization, improves SOC visibility.

**Policy-Guarded Model Execution**
- Clarifies execution behavior during the ENFORCE state
- Applies additional controls before model execution
- Restricts execution scope and monitoring boundaries

**Quarantine Visibility**
- Structured quarantine logging
- Improved threat traceability
- Enhanced incident investigation support

**Response Auditing**
- Logs outbound responses
- Provides end-to-end audit coverage
- Extends visibility beyond ingress events

**Input Normalization**

Safely handles:
- None
- malformed requests
- unexpected input types

Reduces runtime exceptions, improves platform stability.

**Empty Input Rejection**
- Rejects malformed requests before processing
- Reduces unnecessary compute usage
- Strengthens validation boundaries

## Security Controls

### Tier 1 Controls
- Regex attack detection
- Canary token protection
- Allow-list enforcement
- Hard policy violations
- Immediate rejection logic

### Tier 2 Controls
- Behavioral analysis
- Input quality scoring
- Output monitoring
- DLP pattern inspection
- Risk confidence modeling

### Risk Fusion Engine

The Risk Fusion Engine combines security signals to determine final enforcement actions.

The model itself does not determine security outcomes. The control plane remains the authoritative enforcement authority.

### Validation Capabilities
- Attack simulation harness
- Adversarial testing framework
- Expected-versus-actual verification
- PASS / FAIL evaluation
- Security rule validation
- Detection confidence tuning

## Deployment Architecture

### Local Development

```
Run Tests
    ↓
Validate Environment
    ↓
Build Docker Image
    ↓
Run Container
```

### Production

```
Azure Function App
    +
OpenTofu / Terraform
    +
Azure Identity Controls
    +
Centralized Logging
```

Infrastructure remains separate from AI execution and is designed to support governance, auditing, and policy enforcement.

## Certification Alignment

| Domain | Certification |
|---|---|
| Flow Control | Network+ |
| Policy Enforcement | Security+ |
| Detection & Triage | CySA+ |
| Cloud Infrastructure | AZ-104 |
| Identity & Governance | SC-500 |
| Infrastructure as Code | OpenTofu / Terraform Associate |

## Project Structure

```
adversarial-ai-control-plane/
├── README.md
├── requirements.txt
├── control_plane/
│   └── security_control.py
├── docs/
│   ├── README.md
│   ├── notes.md
│   └── threat-model.md
├── infra/
│   └── Dockerfile
├── scripts/
│   └── open-ai-project.sh
└── src/
    ├── mission_start.py
    ├── mission_start_v1.py
    └── output.txt
```

### Repository Organization

- **README.md** -- Project overview, architecture, deployment model, and security philosophy.
- **requirements.txt** -- Python package dependencies.
- **control_plane/** -- Core security control plane implementation.
- **src/** -- Supporting application source code.
- **docs/** -- Threat models, architecture notes, and project documentation.
- **infra/** -- Infrastructure provisioning and deployment configurations.
- **scripts/** -- Helper scripts for testing, automation, and operations.

## Project Statement

I built an asynchronous adversarial AI control plane that intercepts all inputs and outputs, applies deterministic validation and tiered policy enforcement, isolates malicious behavior, and records every decision through structured auditing. Security decisions are computed outside the model using independently governed control logic, ensuring they remain explainable, auditable, and resistant to model manipulation.

## Security Philosophy

**Security decisions happen outside the AI, not inside it.**

The control plane serves as the authoritative enforcement boundary between users and AI systems, ensuring that validation, monitoring, policy enforcement, and auditing remain independent from the model itself.

---

## Appendix: Current MVP Implementation (Docker / FastAPI Build)

Everything above is the target architecture and project narrative. This
section documents what is actually running today in the working proof of
concept, kept clearly separate so the two don't get conflated -- this is
the part to check before anyone asks "show me the code" for a specific
claim above.

**Environment note:** development is currently happening solely on the MSI
Vector 16 HX (Windows 11 Pro, Docker Desktop, WSL2 backend). The Minisforum
X1 Pro-470 is reserved for later, once it becomes the dedicated 24/7
infrastructure node described above.

### Implemented and running

- FastAPI async service (`control_plane/main.py`) fronting a local Ollama instance, port 8443 only
- Input scanning via LLM Guard -- PromptInjection, Anonymize (PII/DLP), TokenLimit -- the current stand-in for "Tier 1 Hard Controls" / input validation above
- RBAC -- two roles (`admin`, `user`), API keys hashed (SHA-256) and stored in Redis, never in plaintext
- Rate limiting -- fixed-window counters in Redis, keyed per API key
- **ISOLATE, for real:** a flagged prompt triggers an actual Docker SDK call that disconnects the model container from every network it's on -- not a log-only quarantine flag
- Redis and Ollama both run on `internal: true` Docker networks, unreachable except through the control plane
- Admin-only endpoints for issuing new API keys and manually reconnecting an isolated container

### Described above, not built yet

- MFA enforcement
- Canary token protection
- Risk Fusion Engine / 0-100 composite risk scoring (today it's pass/fail per scanner, not a fused score)
- Tier 2 behavioral analysis
- Structured severity logging (LOW/MEDIUM/HIGH/CRITICAL) for SIEM ingestion
- Async task lifecycle tracking (`self.tasks`) and graceful shutdown handling
- Output-side DLP inspection (current scanning is input-side only)
- Attack simulation / adversarial testing harness with PASS/FAIL evaluation
- Azure Function App production deployment path (current deployment is Docker Compose on a single host)

### Repo layout: resolved

`control_plane/main.py` (FastAPI + LLM Guard library + Redis RBAC + Docker
network isolation, from the working build above) is the canonical
implementation. `security_control.py` and `mission_start.py` were an
earlier exploratory pipeline design and now live in `archive/` rather than
`control_plane/` or `src/` -- kept for reference, not active development.
The real layout:

```text
control-plane/
  docker-compose.yml
  control_plane/
    main.py
    requirements.txt
    Dockerfile
  infra/
    main.tf
  archive/
    proxy-variant/       -- earlier standalone proxy + separate llm-guard-api service
    pipeline-concept/     -- security_control.py / mission_start.py, Tier1/2 + Risk Fusion design
```

**Ideas from the archived pipeline concept worth porting into the canonical
build, queued on the roadmap above:**
- Egress/output scanning -- the archived design's `evaluate_output()` step
  checked model responses for leaks; the canonical build currently only
  scans input, which is a real gap given "Output monitoring and DLP
  inspection" is listed as a core feature above.
- Canary token detection -- plant a known secret in context, alert if it
  ever appears in a response. Simple to add, high signal.

**Known bugs in the archived code, noted so they don't get pulled back in
blind:** the pipeline-concept variant hardcoded every user's trust score to
0.95 regardless of identity (defeats the purpose of RBAC), dropped the
`canary_token` constructor argument so canary detection may be
non-functional even where it's called, and widened its trusted-registry
entry from a specific API path to an entire domain. The proxy-variant
replaced its LLM Guard classifier call with a bypassable substring
blocklist. None of this is wrong to have explored -- just don't treat
either archived file as production-ready if it gets revisited later.

docs: align README with actual implementation, add MVP status appendix

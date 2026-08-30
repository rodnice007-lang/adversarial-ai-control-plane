# AI Security Control Plane (AASCP) -- starter scaffold

Inline security proxy in front of a local Ollama instance: every prompt
gets scanned and rate-limited before it reaches the model, and a flagged
prompt trips real network isolation, not just a log entry.

## Where this runs right now

```text
MSI Vector 16 HX (Windows 11 Pro, RTX 5070 Ti)
 |
 +-- Docker Desktop (WSL2 backend)
 +-- control-plane   FastAPI + LLM Guard + RBAC, port 8443 only
 +-- redis           state-internal network only, requirepass required
 +-- ollama          model-internal network only, CUDA on the 5070 Ti
```

Laptop-first, deliberately. The Minisforum X1 Pro-470 becomes the 24/7 host
later -- see Later below for when that move actually makes sense.

## Roadmap

```text
NOW
+-- Network+
+-- Docker / Linux fundamentals
+-- Terraform basics
+-- Prompt logging + risk-score / reject-allow logic in the control plane
+-- RBAC + Redis -- already built, keep extending, don't re-litigate

NEXT (after Network+)
+-- Security+ / CySA+
+-- Deeper Azure work
+-- n8n automation -- once there's a real system to automate
+-- Egress/output scanning -- check model responses for leaked secrets or
+   DLP-relevant content, not just input-side scanning (currently missing)
+-- Canary token check -- plant a known secret in system context, alert if
+   it ever appears in a model response

LATER
+-- Move the stack to the Minisforum X1 Pro-470 as a dedicated 24/7 node
+-- Proxmox
+-- pfSense / OPNSense
+-- Wazuh
+-- Security Onion
+-- PRTG monitoring
```

Virtualization and the SOC stack come after the Minisforum move, not
before it -- they should solve a real problem you have by then, not get
stood up speculatively ahead of need.

## What's already running

```text
Docker stack running
FastAPI            healthy
Ollama              healthy
LLM Guard           healthy
RBAC (Redis-backed) healthy -- admin + user roles, key issuance, rate limits
Chat UI                     -- pending: Open WebUI vs. LibreChat decision
```

That's a real milestone. Worth remembering next time a fresh roadmap
document describes this stack as if none of it exists yet.

## Model: small on purpose, for now

`DEFAULT_MODEL` defaults to `qwen2.5:3b` -- deliberately small while you're
testing routing, logging, and RBAC rather than model quality. Same family
as the eventual production target (Qwen 2.5 14B), so scaling up later is a
config change, not a rewrite:

```
$env:DEFAULT_MODEL = "qwen2.5:14b"
```

At 3B, expect it to run comfortably on the RTX 5070 Ti with room to spare --
useful headroom while Docker Desktop, VMware, and everything else share the
same laptop at the same time.

## Inference backend: CUDA on the RTX 5070 Ti

Straightforward CUDA path, same as any modern NVIDIA GPU on Windows -- no
passthrough, no OCuLink, since this runs on the laptop's own dGPU directly.
GPU access into the `ollama` container requires NVIDIA CUDA support enabled
for WSL2 in Docker Desktop's settings.

## RBAC

Two roles: `admin` and `user`. API keys are never stored in plaintext --
only a SHA-256 hash lives in Redis (`rbac:keys`), mapped to a role.

**Bootstrapping the first admin key:** set `ADMIN_API_KEY` before first run.
On startup, the control plane hashes it and seeds it into Redis with the
`admin` role if it isn't already there.

```
$env:ADMIN_API_KEY = "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

**Minting keys after that** goes through the admin, not the env var:

```
curl -X POST https://<host>:8443/v1/admin/keys \
  -H "X-API-Key: <admin key>" \
  -H "Content-Type: application/json" \
  -d '{"role": "user"}'
```

**Calling the chat endpoint** requires any valid key:

```
curl -X POST https://<host>:8443/v1/chat \
  -H "X-API-Key: <user or admin key>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello"}'
```

**Reconnecting after an isolation trigger** is admin-only:

```
curl -X POST https://<host>:8443/v1/admin/reconnect -H "X-API-Key: <admin key>"
```

Rate limiting is keyed on the API key's hash, not source IP -- each identity
gets its own 30-requests-per-60-seconds budget.

```text
Not yet built:
  key revocation
  key expiry
  per-role scanner threshold overrides
```

## LLM Guard thresholds: calibrate before trusting them

Starting points, not finished values:

```
PROMPT_INJECTION_THRESHOLD=0.5   # LLM Guard's documented default
ANONYMIZE_THRESHOLD=0.5          # library default is 0 -- that flags nearly everything
TOKEN_LIMIT=4096
```

```text
Calibration workflow
1. Run known-benign prompts through /v1/chat -- confirm none get blocked
2. Run adversarial prompts from the Kali VM once the stack is up --
   check logs for "blocked prompt" and "borderline score" entries
3. Adjust one threshold at a time, re-run both batches
```

**This scanner will not catch everything on its own.** LLM Guard's
PromptInjection scanner is a single classifier, and social-engineering-style
jailbreaks phrased as innocuous requests have been observed slipping past it
in real-world testing. RBAC and reviewing model output still matter, even
with a well-tuned threshold here.

## Redis: rate limiting and session state

- Its own `state-internal` Docker network, never bridged to `edge` or
  `model-internal`.
- `requirepass` is required -- compose fails to start if `REDIS_PASSWORD`
  isn't set, rather than silently running with no auth.

```
$env:REDIS_PASSWORD = "use a real generated secret here"
docker compose up --build
```

## Container isolation

```text
edge             control plane's side -- only this publishes a port (8443)
model-internal   ollama only, no route out except via control-plane
state-internal   redis only, never bridged to edge or model-internal
```

On a flagged prompt, the control plane calls the Docker SDK to disconnect
the model container from every network it's on.

**Test this explicitly, don't assume it.** Docker Desktop on Windows runs
containers through a WSL2 backend, and WSL2's virtual networking layer
doesn't always behave identically to a native Linux Docker daemon. Confirm
`docker network disconnect` actually cuts reachability under your specific
setup -- if it doesn't, switch Docker Desktop to Hyper-V isolation mode.

## Before running this for real

```text
+-- Put TLS in front of port 8443 -- it currently serves plain HTTP internally
+-- Decide what "isolated" means operationally: page someone? auto-reconnect
    after a cooldown? stay down until a human reviews the logs?
+-- Pick the chat UI (Open WebUI vs. LibreChat) and map its auth to RBAC
```

## Project data

If you're routing project data to a second drive on this host:

```
$env:PROJECT_DATA_PATH = "D:\project-data"
docker compose up --build
```

## Layout

```text
control-plane/
  docker-compose.yml       quick local run
  control_plane/
    main.py                FastAPI app: scan -> forward or isolate
    requirements.txt
    Dockerfile
  infra/
    main.tf                OpenTofu equivalent, local state only
```

## Running it

```
docker compose up --build
curl -X POST localhost:8443/v1/chat -d '{"prompt": "hello"}'

docs: add operational build notes (RBAC, calibration, roadmap)

# Project Journal: Adversarial AI Control Plane (AASCP)

A running record of what's actually been built, verified, corrected, and
decided -- kept honest on purpose, including the mistakes and dead ends,
since that's the part worth more to an employer than a polished summary.

---

## What This Project Is

A local, security-focused inference gateway sitting between users and a
locally-run LLM (Ollama), enforcing RBAC, prompt/PII scanning, rate
limiting, and real network isolation on a threat detection -- built as a
hands-on homelab project alongside Network+/Security+/CySA+/AZ-104
certification study. The build discipline throughout has been: verify
before trusting, defer anything not solving a real problem yet, and keep
documentation honest about what's actually running versus what's planned.

---

## Environment

**MSI Vector 16 HX** (development workstation, stays Windows)
- Intel Core Ultra 9 275HX, 64GB RAM, RTX 5070 Ti (16GB VRAM)
- 2TB internal NVMe + 2TB Samsung 990 Pro NVMe (both internal, confirmed)
- HP Thunderbolt 4 Ultra 180W G6 Dock (corrected from an earlier "Anker
  Prime 14-in-1" mislabel in draft documentation)
- VMware Workstation Pro (confirmed free for personal use) running Kali
  Linux for adversarial/red-team testing
- Anker Nano Power Strip, XP-Pen Deco Pro XLW (screenless drawing tablet)

**Minisforum AI X1 Pro-470** (24/7 infrastructure node, migrating to Linux)
- AMD Ryzen AI 9 HX 470, 64GB DDR5 (corrected from an earlier "32GB" draft
  error), 2TB NVMe SSD, dual 2.5GbE, dedicated OCuLink port + dual USB4
- Currently Windows 11 Pro; migrating to Ubuntu Server 24.04 LTS
- eGPU: DEG1 dock connected via **native OCuLink** (PCIe 4.0 x4, up to
  64GT/s) -- verified against actual hardware spec sheets after two
  incorrect "it's actually USB4" corrections earlier in the process
- GPU: RTX 3060 12GB being swapped for an **AMD RX 9070 XT 16GB** (RDNA 4,
  gfx1201) -- parts arriving 9/8/26

**Network**
- UniFi Flex Mini 2.5G switch (USW-Flex-2.5G-5) sitting between both nodes
  -- not a direct link, corrected from an early diagram that omitted it
- Cat6a UTP 24 AWG, ~30ft run + 4-6ft patch cables, 2.5GbE throughout
- Static addressing: MSI Vector 192.168.1.10/24, Minisforum 192.168.1.20/24

**Storage**
- Samsung T7 2TB external -- archive/backup drive (corrected from an
  earlier diagram that mislabeled it as a second internal Samsung 990 Pro)

---

## Architecture Journey: How We Got Here

**Started as a networking question.** The project began with a bottleneck
question -- why splitting model weights across a LAN link kills inference
speed, versus keeping inference local and only routing text over the
network. That physics-first framing shaped every later architecture
decision: nothing crosses the network except prompts/responses, model
weights and GPU access stay local to whichever machine serves them.

**Reconciled a buzzword-heavy vision document against a real build.** An
early architecture document described an idealized system (Risk Fusion
Engine, MFA, canary tokens, async task lifecycle tracking, Tier 1/2
classification) as if already built. Resolved by keeping the vision
document intact but adding an honest "Current MVP Implementation" appendix
that draws a clear line between what's real and what's aspirational --
avoiding the trap of documentation that outpaces the actual code.

**Exercised scope discipline repeatedly, on purpose.** Evaluated and
consciously deferred or declined, each on its own merits rather than
reflexively: Redis and n8n (deferred until the control plane had a reason
to need them -- later un-deferred once RBAC genuinely needed session
storage), Proxmox/pfSense/Security Onion/Wazuh/PRTG (parked for a later
phase, not blocking current work), KVM/QEMU (correct tool, but only once a
real GPU-passthrough-to-a-VM need exists), and three external tools
(Graft, AirLLM, z.ai) each evaluated and declined for concrete,
architecture-specific reasons rather than vague dismissal.

**Discovered and reconciled three divergent control-plane
implementations.** Over the course of development, three different,
disconnected versions of the "control plane" existed simultaneously: a
FastAPI + `llm-guard` library scaffold, a standalone proxy calling a
separate `llm-guard-api` microservice (which had also regressed to a
bypassable substring blocklist), and a `security_control.py`/
`mission_start.py` pipeline concept. Investigation revealed
`security_control.py` was a confirmed-dead stub (its own `evaluate_input`
always returned the same hardcoded PASS result), while
`continuous_control_plane.py` -- imported by `mission_start.py` -- was
real, tested, working policy logic that had never been wired into the
actual HTTP-facing proxy. Resolved by archiving the dead stub and wiring
the real policy logic into the canonical `main.py`.

---

## What's Actually Built and Verified Working

Confirmed via an actual end-to-end test (not just code review) on the
laptop, Windows/CUDA, `qwen2.5:3b`:

- **RBAC** -- SHA-256 hashed API keys in Redis, `admin`/`user` roles, key
  issuance and container-reconnect endpoints restricted to admin
- **Rate limiting** -- Redis fixed-window counters, keyed per API key hash
  (not source IP, so multiple clients behind one LAN IP don't share a budget)
- **LLM Guard scanning** -- PromptInjection, Anonymize (PII/DLP),
  TokenLimit, with calibrated thresholds (env-var configurable) and
  borderline-score logging for future threshold tuning
- **Identity/action policy** -- `continuous_control_plane.py` wired into
  the request path, evaluating role/action/MFA-stub before scanning
- **Real isolation trigger** -- a flagged prompt calls the Docker SDK to
  disconnect the Ollama container from every network it's on; this is an
  active circuit breaker, not a log-only flag
- **Ollama-native API compatibility** -- `/api/chat`, `/api/tags`,
  `/api/version` implemented so Open WebUI's native connection type works
  against the control plane directly
- **Three isolated Docker networks** (`edge`/`model-internal`/
  `state-internal`) -- Redis and Ollama unreachable except through the
  control plane, no published ports on either
- **Performance**: shared `httpx.AsyncClient` (was recreating one per
  request), Ollama `keep_alive` set to avoid repeated cold-start reloads

---

## Real Debugging Wins Worth Remembering

The friction, documented on purpose:

- **A dependency regression that had nothing to do with our code**: a
  recent `transformers` release (4.55.2+) broke PyTorch-only installs by
  unconditionally trying to import a TensorFlow-specific class. Diagnosed
  via the actual traceback, confirmed via search as a known upstream
  issue, fixed with a version pin -- not a guess.
- **A hardcoded RBAC vulnerability caught before it shipped**: an earlier
  draft of `continuous_control_plane` wiring would have hardcoded every
  user's trust score to 0.95 regardless of identity, defeating the point
  of RBAC entirely. Caught during review, never merged.
- **Three separate small-scale GitHub UI mistakes, each diagnosed and
  fixed**: a rename field that silently appended instead of replacing
  (compounding into a nested `control_plane/archive/pipeline-concept/
  archive/pipeline-concept/` mess), a markdown paste that lost all
  formatting because it was copied from a rendered view instead of raw
  source, and a stray commit-message line that got typed into file content
  instead of the commit message box across several files (breaking
  `docker-compose.yml`'s YAML parsing specifically).
- **An orphaned, exposed container stack discovered by accident**: three
  containers (`fastapi-proxy-firewall`, `open-webui`, `llm-guard-api`) from
  an earlier compose file version were still running, unpublished ports
  bound to `0.0.0.0` (reachable from the whole LAN), invisible to
  `docker compose down` because the current compose file no longer defined
  those service names. Found via a routine `docker ps` check before
  assuming "all stopped."
- **A hardware spec corrected twice, in opposite directions, before
  landing on the truth**: the Minisforum-to-eGPU link was first stated as
  64 Gbps OCuLink, "corrected" to USB4 based on two different diagrams
  that both turned out to be wrong, then confirmed via the actual
  manufacturer spec sheet that OCuLink was right all along -- a genuine
  lesson in not trusting a "corrected" diagram just because it looks
  more official than the original claim.

---

## Tools Evaluated and Declined

Each on its own merits, not reflexively:

- **Graft** (repo-to-knowledge-graph tool) -- built for Claude Code CLI
  sessions on large codebases; this project's workflow (chat + GitHub web
  editing) and current codebase size don't match its value proposition.
- **AirLLM** (layer-streaming inference for huge models on tiny VRAM) --
  solves a VRAM-scarcity problem this project doesn't have (16GB fits the
  14B target model fine via normal quantization), and would require a
  separate serving architecture outside Ollama.
- **z.ai** (Zhipu AI's cloud GLM API) -- directly conflicts with the
  project's founding "locally locked down, no cloud" requirement. Flagged
  as a legitimate option only for a separate, external benchmark harness,
  never as part of the isolated data plane.
- **KVM/QEMU** -- correct tool for real GPU passthrough to a VM, but only
  once that need actually exists; not added preemptively.

---

## Verified Facts (Not Assumed)

Things worth remembering were checked, not guessed:

- VMware Workstation Pro is free for personal use (current, confirmed).
- VMware Workstation has **never** supported PCIe GPU passthrough on any
  host OS -- an architectural/product-tier decision, not a kernel
  compatibility issue that might improve with updates.
- PRTG's core server requires Windows; no Linux-native core exists.
- ROCm 7.2 added native RDNA 4 (`gfx1201`) support -- no
  `HSA_OVERRIDE_GFX_VERSION` hack needed for this specific card.
- The RX 9070 XT's "1,557 TOPS" marketing figure is INT4-with-sparsity,
  the best-case scenario for AI upscaling workloads -- not representative
  of real dense LLM inference throughput.
- The Windows 11 Pro license on the Minisforum is embedded in UEFI
  firmware (confirmed via `Get-CimInstance`), meaning any future
  reinstall on this exact hardware auto-activates.

---

## Hardware Migration Status

**Done:**
- Windows 11 ISO downloaded and saved to the T7 (`minisforum-recovery/`)
- Ubuntu Server 24.04 LTS installer USB built via Rufus
- `docker-compose.minisforum.yml` written and committed -- corrected
  Linux/ROCm target config (three-network isolation preserved, ROCm device
  passthrough, no CUDA/nvidia references, no HSA override hack)
- `docs/minisforum-linux-migration-runbook.md` written and committed --
  full four-phase runbook (backup/verify, wipe/install, ROCm/Docker setup,
  deploy/verify) with checkpoints at each phase

**Outstanding, blocking the actual migration:**
- Windows recovery USB (separate physical drive from the Ubuntu one) --
  ordered, not yet arrived
- Disk image backup of the Minisforum's current Windows install to the T7
  -- cannot happen until the box is physically opened and booted
- The physical hardware swap and OS migration itself -- waiting on both
  the recovery USB and the RX 9070 XT, both landing around 9/8/26

---

## Current State, Plainly

Software: built, tested, genuinely working end-to-end on the laptop.
Documentation: matches what's actually running, corrected multiple times
when it drifted. Hardware: fully planned and staged, execution waiting on
physical parts and a completed safety net -- not rushed ahead of either.

---

## Changelog

Appended automatically going forward, whenever a real change is made or a
real issue is found -- short, dated, specific. This is the running log;
the sections above are the standing summary, updated less often.

### 2026-09-02
- Created this journal and its changelog section. Standing process
  established: from here forward, changes and issues get a dated entry
  here automatically, ready to paste into VS Code and push -- no need to
  ask each time.




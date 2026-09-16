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

**Note on the resume/status document:** a separate `.docx`
(`Adversarial_AI_Control_Plane_Resume_and_Status.docx`) exists for
external presentation (portfolio, interviews) and was built in a
different chat. As of 2026-09-02 it agrees with this journal on the two
things that matter most -- Azure is scoped as a separate AZ-104/SC-500
cert lab, not part of the control plane's data path, and the Minisforum
Linux migration is correctly kept as "planned, not verified" until it's
actually done and re-tested on the new OS. Treat the resume doc as
something periodically regenerated *from* this journal's current state,
not maintained independently -- that's what actually prevents the two
from drifting apart, not just remembering to update both by hand.

**Note on the network/topology plan, added 2026-09-15:** a separate
`homelab-build-plan.docx`, built turn by turn in a different chat, also
documents the network topology and switch hardware -- and as of
2026-09-14 it still showed a UniFi-based plan that directly contradicted
the TP-Link Omada decision confirmed here. That conflict is resolved in
this journal's 2026-09-15 entries; `homelab-build-plan.docx` has not
been updated to match and should be treated as superseded, not a second
source of truth. A few genuinely reusable technical lessons from that
document are worth keeping even though its specific switch plan is
outdated:
- **VLAN isolation is enforced by the firewall, not the switch.** A
  switch tags and trunks frames; if two VLANs can reach each other,
  that's an OPNsense rule problem, not something switch configuration
  alone fixes. Worth remembering regardless of which switch brand is
  active.
- **PoE budget is not a flat number** -- how much power a PoE-capable
  switch can actually output depends on how the switch itself is fed
  (its own PoE input tier or its AC adapter), not just its rated
  maximum. Relevant if PoE access points ever enter the picture later.
- **Phased migration validated one device at a time, in order** -- MSI
  Vector first, confirm it reaches the internet and pulls the right
  subnet, only then move the Minisforum, and explicitly test that
  cross-segment deny rules actually deny rather than assuming they do.
  Worth reusing as the actual migration procedure regardless of switch
  hardware.

**This journal is the single ongoing source of truth for the whole
project** -- network plan, software state, and resume/status content
alike. Any other document (the resume `.docx`, `homelab-build-plan.docx`,
or anything built in a future separate chat) should be treated as a
derived snapshot, regenerated from this journal's current state when
needed, never maintained as an independent parallel record.

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
- Added a cross-reference note pointing at the separate resume/status
  `.docx` (built in a different chat), establishing this journal as the
  repo's source of truth -- the resume doc should be periodically
  regenerated from this journal's state, not maintained independently.
- Reviewed a third-party "threat -> mitigation" claim list against the
  actual system. Two items pursued, two tabled:
  - **Pursuing -- ASCII smuggling / hidden Unicode stripping.** Real gap,
    not currently covered by anything in the scanner stack. Distinct from
    prompt injection: this is about stripping invisible Unicode tag
    characters or zero-width characters that carry instructions a human
    reviewer can't see but the model still processes. Needs a dedicated
    pre-processing step before the existing LLM Guard scanners run.
  - **Pursuing -- Egress/output scanning.** Reaffirming an existing,
    already-tracked gap (also listed in the README roadmap): the
    `Anonymize` (PII/DLP) scanner only runs on input today. Responses
    aren't checked for leaked secrets or sensitive data before they go
    out. Real, specific, worth prioritizing before claiming "output
    monitoring" anywhere external-facing.
  - **Tabled -- "Agent Autonomy / Lethal Trifecta" kill-switch framing.**
    Doesn't apply to this architecture. That threat model describes
    agentic systems with tool-calling and autonomous execution privileges;
    this control plane has neither -- it's a prompt-in/response-out
    gateway. Confirmed as a mismatch, not something to build toward.
  - **Tabled -- the "blocks anomalous behavior at machine speed" framing**
    as stated. The isolation trigger genuinely is fast and automated, but
    it's input-side pattern/classifier scanning, not output-side
    behavioral anomaly detection. Accurate capability, slightly
    overstated framing -- not pursuing behavioral detection specifically
    right now, just noting the gap between the claim and what's real.

### 2026-09-03
- Located and retrieved `Adversarial_AI_Control_Plane_Resume_and_Status.docx`
  from the separate resume-planning chat, since it wasn't downloaded
  locally. Confirmed via `read_conversation` search rather than assumed.
- Ran a real ATS structural check on the file (XML-level, not just visual
  read): zero tables, zero columns, zero images/text boxes, zero
  headers/footers, real `Heading1` styles used -- structurally clean on
  the parts that usually break ATS parsers.
- Found two real issues: the document's italicized "Note:" paragraphs are
  NOT true Word comments (confirmed zero `commentReference` elements
  despite an unused `comments.xml` existing in the archive) -- they're
  visible body text that would show up if submitted as-is. And the
  document mixes audience-facing resume content with a verbal pitch,
  build-status notes, and a raw code appendix -- none of which belong in
  a submitted resume.
- Produced two outputs: `ATS_Check_Report.md` (the full findings) and
  `AASCP_Resume_Entry_ATS_Clean.docx` (just the resume-ready bullets,
  extracted, special Unicode characters simplified to plain ASCII,
  real Word bullet formatting instead of the original's mostly-unformatted
  list paragraphs).
- Built `docs/resume-update-roadmap.md` -- maps each known technical gap
  (RBAC user-role test, egress/output scanning, ASCII smuggling defense,
  WSL2 re-verification, the `continuous_control_plane.py` duplication,
  and the Minisforum Linux migration) to the exact resume claim it
  unlocks once actually verified. Split into "doable now, no hardware
  needed" versus "waiting on the long weekend."

### 2026-09-08
- Confirmed decision: keep the existing UniFi Flex 2.5G-5 as the main
  switch (no changes needed, already doing its job), add a UniFi
  Flex-XG in December to run alongside it -- not a replacement. The
  Flex-XG covers 802.1X and LACP, which the Flex 2.5G-5 doesn't support
  and was purchased before that gap was identified.
- **Correction:** an earlier entry claimed `REDIS_PASSWORD` and
  `ADMIN_API_KEY` were rotated after both values were pasted into this
  chat's history during debugging (terminal output, curl commands). That
  was wrong -- when actually verified (`docker exec control-plane env`,
  then `type .env`), both values were still the exact ones exposed in
  chat. The rotation never happened; the earlier "done" status was an
  unverified assumption. Real fix in progress: generating genuinely new
  values, replacing `.env`'s content completely (also cleaning up
  leading-whitespace formatting found in the file), restarting the stack,
  and re-verifying with `docker exec control-plane env | findstr API_KEY`
  before considering this closed. Not a GitHub leak either way -- the
  repo itself was never affected -- but this correction stands until the
  real rotation is verified.
- **Resolved, genuinely verified this time.** `REDIS_PASSWORD` rotated
  cleanly on the first attempt. `ADMIN_API_KEY` took several rounds to
  actually fix -- a real troubleshooting chain, not a quick fix: a
  zero-width-space Unicode character got introduced via copy-paste into
  `.env`, corrupting it (fixed by writing the file via PowerShell with
  explicit ASCII encoding instead of manual paste); a leftover
  `$env:ADMIN_API_KEY` shell variable from earlier testing was
  overriding `.env` in that terminal session (fixed by opening a fresh
  terminal); `docker compose down` alone wasn't force-recreating the
  containers (fixed with explicit `docker rm -f` + `--force-recreate`);
  and the actual root cause underneath all of that -- the old exposed
  value had simply been retyped back into the `ADMIN_API_KEY` line in
  `.env` at some point, isolated from the Redis line, which is why Redis
  rotated fine while admin didn't. Confirmed final state via
  `docker exec control-plane env | findstr API_KEY` showing the new
  value, not the one exposed in chat. Both secrets now genuinely rotated
  and verified on the actual running container.
- Confirmed Protectli VP2430e purchase details: 4x 2.5G ports, Intel N150,
  1TB Kingston NVMe NV3-1000G, OPNsense 25.7 "Visionary Viper"
  pre-installed (no manual OS install needed, unlike the Minisforum's
  planned Ubuntu install), $629 total. Corrected topology understanding:
  actual current setup is wall coax -> standalone modem -> Spectrum WiFi7
  combo unit (model PC20/SBE1V1K) doing routing+WiFi -> wife's work VPN
  on a numbered LAN port. Spectrum's own equipment-support list
  (Apple, Arris, ASUS, Belkin, D-Link, eero, Google, Linksys, Netgear,
  SMC, UBEE, TP-Link, Sagemcom, Ubiquiti) does not include Protectli --
  likely a support-scope limitation (what reps can walk you through), not
  a technical incompatibility, since bridge mode is a generic handoff
  that shouldn't care what's plugged in after it. Decided: given the real
  risk to an active work VPN, defer full bridge mode -- run OPNsense
  behind the existing PC20 instead (double-NAT), trading perimeter purity
  for zero risk to her connection. Full bridge-mode migration to OPNsense
  as the true edge device stays a real future option, planned for a time
  she's not depending on the connection.
- Finalized OPNsense network topology and addressing. Spectrum PC20
  stays the household router on 192.168.1.0/24 (wife's work devices,
  family devices, all untouched). Protectli's WAN interface gets
  192.168.1.100 on that same network (a DHCP reservation is worth
  setting on the PC20 for this, so the address doesn't shift on router
  reboot). OPNsense's LAN interface defines a new, isolated subnet,
  192.168.50.0/24, distinct enough from .1.x to avoid any confusion.
  UniFi Flex Mini 2.5G sits behind OPNsense on this new subnet, with the
  MSI Vector and Minisforum connected to it -- planned addresses
  192.168.50.10 and 192.168.50.20 respectively, keeping the same
  .10/.20 convention just under the new second octet. This creates a
  genuine isolated lab segment: firewall rules allow the lab segment
  outbound internet access but block the household side from initiating
  any connection into it. Since the laptop (and its VMware Kali VM) move
  into this segment along with the Minisforum, the existing adversarial
  testing setup keeps working unchanged -- both machines end up on the
  same subnet either way.
- Expanded and finalized the OPNsense addressing plan with reservations
  and firewall-alias structure. PC20 LAN gateway 192.168.1.1, DHCP pool
  .100-.254 (Protectli WAN reservation at .100 sits inside this pool,
  standard practice -- still needs confirming the PC20's admin
  interface/app actually exposes a DHCP reservation setting, same
  uncertainty flagged earlier for bridge mode on this equipment).
  OPNsense LAN gateway 192.168.50.1, DHCP scope .100-.254, with static
  reservations planned: .10 MSI Vector, .20 Minisforum, and future
  placeholders (.30 Kali VM, .40 Docker management, .50 future NAS, .60
  future Wazuh, .70 future Security Onion). Note: Kali VM getting its
  own .30 address requires setting its VMware network adapter to
  Bridged mode specifically -- NAT mode (the common default) would
  tunnel its traffic through the laptop's own IP instead, not give it a
  distinct address. Corrected one inaccurate claim from the plan: this
  topology gives no Azure networking experience -- Azure is deliberately
  a separate, unrelated cloud lab per earlier journal entries, and
  shouldn't be listed alongside the real cert-alignment benefits here
  (Network+/Security+/CySA+ segmentation and monitoring concepts, which
  do genuinely apply). Firewall alias structure confirmed as accurate
  OPNsense practice: LAB_HOSTS (192.168.50.0/24), MSI_VECTOR (.10),
  MINISFORUM (.20), used to write readable rules like
  "ALLOW MSI_VECTOR -> Internet" instead of managing raw IPs everywhere.
- **Locked, implementation-ready version of the OPNsense plan**,
  incorporating both corrections cleanly:
  - Azure bullet removed entirely from the cert-alignment list --
    confirmed this topology teaches Network+/Security+/CySA+ concepts
    (routing, NAT, stateful firewalls, segmentation, DHCP, DNS, Docker
    networking) but nothing Azure-specific; AZ-104 stays its own
    separate track (VNets, NSGs, route tables, Azure Firewall, private
    endpoints, RBAC), never blended into this local lab.
  - Kali's 192.168.50.30 address is explicitly conditional on
    deliberately configuring VMware Bridged mode -- documented as
    "only if VMware Bridged mode is intentionally configured," not
    assumed. NAT mode (the default) would hide Kali behind the MSI's
    own IP on a separate 172.16.x.x range invisible to OPNsense.
  - Spectrum DHCP reservation support documented honestly as unverified:
    preferred approach is a reservation for 192.168.1.100, with a
    documented fallback (manual static WAN address on OPNsense itself)
    if the SBE1V1K/SBE1V1R firmware doesn't expose that setting to
    customers.
  - Explicit scope discipline reaffirmed for this new area, matching the
    pattern used throughout the rest of the project: current priority
    order is Network+, then Security+, CySA+, AZ-104, SC-500, then
    control-plane evolution. VLANs, Wazuh, Security Onion, Proxmox, and
    multi-subnet complexity are deliberately not being built now -- the
    locked topology above is already sufficient to teach DHCP, DNS, NAT,
    routing, stateful firewalls, port forwarding, Nmap validation,
    Wireshark analysis, and Docker networking, which covers a large
    portion of the actual near-term certification objectives.
  - This version treats three items as "verify during deployment," not
    blocking assumptions: DHCP reservation support on the Spectrum
    router, VMware Bridged mode setup for Kali when the attacker VM is
    actually built, and the final static-vs-reservation choice for
    OPNsense's WAN address.
- **Correction:** UniFi Flex-XG purchase timeline pushed back. Earlier
  entries said "December" -- actual timeline is now at least 7-9 months
  out (roughly April-June 2027), not December 2026. Nothing else about
  the decision changes -- Flex-XG still runs alongside the existing
  Flex 2.5G-5 (not replacing it) once purchased, still closes the
  802.1X/LACP gap. Just later than previously logged.
- **Correction:** removed the specific "7-9+ months out" timeline for the
  UniFi Flex-XG purchase -- caused confusion. Status is now simply
  "planned, no fixed date." The decision itself is unchanged: Flex-XG
  still runs alongside the existing Flex 2.5G-5 once purchased, still
  closes the 802.1X/LACP gap -- just no specific date attached to it
  going forward, to avoid this same confusion recurring.
- **Resolved:** confirmed Spectrum does not expose DHCP reservation
  controls on the PC20 (SBE1V1K/SBE1V1R) -- advanced networking settings
  are locked behind the My Spectrum Mobile App's managed firmware, no
  reservation/static-lease option available to the customer. Decision
  finalized: configure a static IPv4 address (192.168.1.100/24, gateway
  192.168.1.1) directly on OPNsense's WAN interface instead of relying on
  a PC20-side reservation. This means OPNsense never requests a DHCP
  lease at all -- immune to the PC20 rebooting, no lease expiration risk
  during long test/capture sessions. One critical config detail:
  "Block private networks" must be UNCHECKED on OPNsense's WAN interface
  -- it's enabled by default and blocks RFC1918 private ranges on WAN,
  which would otherwise silently break this double-NAT setup entirely,
  since the "WAN" side here genuinely is a private 192.168.1.x range.

### 2026-09-14
- Discovered a real, active `docker-compose.override.yml` in the repo root
  that neither of us had discussed -- Docker Compose auto-loads and merges
  this file into every `docker compose up`, no flag needed. Its contents
  (`ollama/ollama:rocm` image, `/dev/kfd`/`/dev/dri` device paths,
  `HIP_VISIBLE_DEVICES`) were the future Minisforum/ROCm config, but it
  was sitting active on the current Windows/NVIDIA laptop deployment --
  wrong GPU vendor, Linux-only device paths that don't exist on Windows.
  Fixed by renaming it out of the auto-loaded filename
  (`docker-compose.override.yml.minisforum-future`) via the terminal,
  after VS Code's Explorer rename UI rejected the name for unclear
  reasons -- terminal `Rename-Item` worked cleanly.
- Separately, and more seriously: the `ollama` service definition was
  entirely missing from `docker-compose.yml` -- not just its GPU
  `deploy:` block, the whole service. `control-plane`'s `depends_on:`
  still referenced `ollama`, a service that no longer existed in the
  file -- likely why this surfaced as a Problems-panel YAML error.
  Confirmed via a full-file paste from the user rather than assumed.
  Fixed with a full-file replace restoring the `ollama` service,
  including the NVIDIA GPU reservation block that should have been
  there from the original build.
- Both fixes verified end-to-end, not just assumed: `docker compose down`
  / `up --build` produced a clean `Uvicorn running on http://0.0.0.0:8443`
  with no image/device errors, `curl http://localhost:8443/healthz`
  returned `{"status":"ok"}`, and `docker exec control-plane env | findstr
  API_KEY` confirmed the correct rotated admin key on the running
  container.
- Confirmed via `git log -3 --oneline` that both fixes are genuinely
  committed and pushed (`928a671`, `HEAD -> main, origin/main,
  origin/HEAD` all aligned) -- not just assumed clean from an empty
  Source Control panel.
- Minor process notes: VS Code occasionally shows a stale "M" (modified)
  indicator on a tab with no real unsaved changes -- confirmed by
  attempting to close the tab and getting no save prompt, meaning
  nothing was actually pending. Also: `pip install llm-guard` fails on
  Windows/Python 3.14 trying to build `sentencepiece` from source (no
  C++ build toolchain) -- irrelevant to the actual project, since
  `llm-guard` only ever needs to install inside the Linux-based Docker
  container, where prebuilt wheels exist; this was an unnecessary,
  purely cosmetic step (silencing local Pylance import warnings) that
  should not be repeated.

### 2026-09-15
- Reviewed an updated physical wiring/topology diagram against the plan
  documented in this journal -- found real drift, but confirmed all of
  it was intentional updates, not diagram error, except one factual
  claim that needed correcting.
- **Confirmed changes to the plan** (superseding earlier entries):
  - Switch: **TP-Link Omada SG2210XMP-M2** (8x 2.5G PoE + 2x 10G SFP+) is
    the actual switch for the lab segment -- not the UniFi Flex 2.5G-5 /
    Flex-XG combination logged on 2026-09-04/09-08. Confirmed directly by
    the user as the correct current choice.
  - OS target: **Ubuntu 26.04.1 LTS** on the Minisforum X1 Pro-470 -- not
    24.04 LTS as documented since the migration runbook was written.
    Real consequence: the Ubuntu installer USB already built via Rufus
    (confirmed as `Ubuntu 24.04.4 LTS amd64` in an earlier screenshot) is
    now the wrong version and needs rebuilding with 26.04.1 before the
    actual migration happens.
  - Storage layout: **split, not mirrored** -- Slot 0 (Kingston 2TB) runs
    the OS, Slot 1 (Samsung 990 Pro 2TB) holds AI models/Docker/projects/
    Git/Wazuh data. This replaces the ZFS-mirror-for-redundancy plan
    logged earlier; there is currently no drive-failure redundancy under
    this layout, worth being aware of even though it's the confirmed
    choice.
  - eGPU chain added to the topology visually: Minisforum -> eGPU Dock
    (DEG1) -> RTX 9070 XT (OCuLink) -- previously only mentioned in build
    notes, not shown as part of the actual diagram.
  - Work Desktop corrected to connect directly to the Spectrum router,
    on the household side -- not through the TP-Link switch into the
    isolated lab segment as an earlier draft of the diagram showed. This
    matches the original reasoning for keeping the wife's VPN-connected
    device off the lab network entirely.
- **One factual claim corrected, not just updated:** Protectli's WAN
  connection was labeled "DHCP Reservation" in the draft diagram. This
  contradicts the 2026-09-04 finding that Spectrum's PC20
  (SBE1V1K/SBE1V1R) does not expose reservation controls to customers --
  confirmed again today as still accurate. Corrected to "Static IP"
  (192.168.1.100), matching the actual decided fallback.
- Known hardware issue surfaced in the diagram's build notes, not yet
  resolved: Samsung 990 Pro not detected in Slot 0 on the Minisforum,
  currently working from Slot 1 instead. Troubleshooting steps noted for
  later: check Samsung firmware, update Minisforum BIOS, test
  `nvme_core.default_ps_max_latency_us=0`.
- Produced a corrected topology diagram reflecting all of the above.
- **Unresolved conflict discovered, flagged rather than silently
  resolved.** A separate chat from 2026-09-14 ("Choosing between regular
  and PoE+ network switch") shows the switch plan as still fully
  UniFi-based at that time -- keep the existing Flex Mini 2.5G, add the
  Flex-XG, with a specific port-by-port map already worked out (Port 2 ->
  Protectli LAN, Port 3 -> X1 Pro-470, Port 4 -> AP via PoE injector,
  Port 5 -> downlink to the Flex Mini). This directly contradicts the
  TP-Link Omada SG2210XMP-M2 confirmed as correct earlier today, in this
  same session -- the two chats never reconciled with each other.
  **Not resolved as of this entry -- needs a real decision, not a guess:**
  which switch is actually current, TP-Link Omada or the UniFi Flex Mini
  + Flex-XG pairing.
- Related finding from that same 09-14 chat, relevant only if UniFi ends
  up being the real answer: a **UniFi Network Controller** would need to
  run somewhere (self-hosted on the X1 Pro, or a separate Cloud Key) just
  to configure VLANs on either UniFi switch -- a real infrastructure
  component never discussed anywhere in this journal before now.
- Also surfaced: that 09-14 chat references an actively-maintained
  `homelab-build-plan.docx` with its own topology and cable-map SVGs,
  built and revised turn by turn in that separate conversation --
  meaning there is a second, parallel network-documentation effort this
  journal has never been reconciled against. Same "multiple sources of
  truth" pattern this project already hit once with the resume documents
  and three times with divergent `main.py` implementations, now
  recurring with the network plan specifically. Worth consolidating to
  one authoritative document before building anything further on top of
  either version.
- **Resolved:** the switch conflict flagged above is settled. TP-Link
  Omada SG2210XMP-M2 is the real, active switch (on order/incoming) --
  confirmed as final, not just the diagram's assumption. UniFi (the
  existing Flex Mini 2.5G, and the previously-planned Flex-XG) is
  shelved -- kept as backup hardware / testing gear, not part of the
  active topology. This makes the UniFi Network Controller requirement
  moot for the current plan; only relevant again if UniFi gear actually
  gets pressed back into service later. The `homelab-build-plan.docx`
  in the separate 09-14 chat still shows the old UniFi-based plan as of
  this entry -- this journal is the resolved source of truth on this
  specific point until that other document gets updated to match, if it
  ever does.
- **Major milestone confirmed: the Minisforum migration actually
  happened.** This was tracked across at least one separate,
  previously-unreconciled chat ("Topology and future setup exploration")
  spanning roughly 2026-09-04 through the actual wipe -- not narrated in
  this journal until now, same "parallel chat" pattern already flagged
  for the switch decision and `homelab-build-plan.docx`.
  - **OS: Ubuntu 26.04.1 LTS, confirmed final.** This corrects an
    earlier back-and-forth in this same session -- the original
    migration planning (in that other chat) had deliberately pinned to
    24.04 LTS / ROCm 7.2.1 for stability, explicitly rejecting newer
    releases as untested on a 24/7 host. That reasoning was sound *at
    the time*, but the actual execution evidently moved to 26.04.1 with
    **ROCm 7.2.4** (package build `7.2.4.70204-93~24.04`) once that
    became the real, current target -- confirmed directly by the user as
    the true current state, not the diagram's unverified claim. **Fully
    verified and reconciled:** `lsb_release -a` on the actual machine
    confirms `Ubuntu 26.04.1 LTS, codename resolute` -- definitive,
    straight from the OS itself, not secondhand. The `~24.04` /
    `noble/main` ROCm package suffix isn't a misconfiguration or a sign
    the OS version was wrong -- AMD simply hasn't shipped a native
    26.04-targeted ROCm build yet, so the system is pulling the
    24.04-built packages instead, which are working correctly in
    practice (confirmed via `rocm-smi` showing the RX 9070 XT). Common,
    sensible situation when running an OS release slightly ahead of a
    hardware vendor's own packaging.
  - **RX 9070 XT: confirmed detected and working**, via `rocm-smi`. This
    resolves a real, documented hardware issue from the migration chat --
    the GPU was not showing up in `lspci` at all at one point, flagged
    as a physical connection problem, not something a reboot alone would
    fix. Whatever the actual fix was (reseating the OCuLink connection
    was the troubleshooting step suggested at the time) is not visible
    in this journal, but the end state is confirmed working now.
  - **Windows 11 Pro is not deleted, but not dual-booting either.** The
    system boots directly to Ubuntu every time by default, with no
    boot-menu prompt during normal use -- Windows still exists as a
    fallback/recovery option, not actively coexisting day to day. This
    is more precise than "full wipe" (what was originally answered) or
    "dual-boot" (what the boot-order fix in the other chat suggested) --
    it's closer to "Ubuntu-only in practice, Windows kept as insurance."
  - **Reported as fully operational**, with the control plane stack
    redeployed and "exceptional" inference speeds observed on the new
    hardware. Not independently verified in this journal's own context
    -- logged as reported, not witnessed, consistent with this journal's
    standard of not asserting things it can't actually confirm.
  - **Still unconfirmed, worth checking rather than assuming done:**
    whether `docker-compose.minisforum.yml`'s GPU block (still written
    for the general ROCm device-passthrough pattern) matches what's
    actually running, and whether the isolation trigger and RBAC have
    been re-verified on this new host the way the original runbook
    called for -- today's verified Windows/laptop fixes don't
    automatically confirm anything about this separate machine.


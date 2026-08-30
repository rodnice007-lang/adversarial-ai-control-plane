import hashlib
import os
import logging
import secrets

import docker
import httpx
import redis
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from llm_guard import scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, TokenLimit
from llm_guard.input_scanners.prompt_injection import MatchType
from llm_guard.vault import Vault
from pydantic import BaseModel

from control_plane.continuous_control_plane import evaluate_control_plane_request

app = FastAPI(title="AI security control plane")
logger = logging.getLogger("control_plane")

docker_client = docker.from_env()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
MODEL_CONTAINER = os.environ.get("MODEL_CONTAINER", "ollama")
MODEL_NETWORK = os.environ.get("MODEL_NETWORK", "model-internal")

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]  # no default -- fail loudly if unset
redis_client = redis.Redis(host=REDIS_HOST, password=REDIS_PASSWORD, decode_responses=True)

# Small model while you're testing routing, logging, and RBAC -- not model
# quality. Same family as the eventual production target (Qwen 2.5) so the
# later upgrade to a bigger checkpoint is a config change, not a rewrite.
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen2.5:3b")

RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60

# --- RBAC ---------------------------------------------------------------
# API keys are never stored in plaintext -- only their SHA-256 hash lives in
# Redis, mapped to a role. ADMIN_API_KEY seeds the very first admin key on
# startup so there's a way in; every key after that gets minted through
# /v1/admin/keys by an existing admin.

RBAC_KEY_HASH = "rbac:keys"
VALID_ROLES = ("admin", "user")


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_role(api_key: str) -> str | None:
    return redis_client.hget(RBAC_KEY_HASH, hash_key(api_key))


def get_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    return x_api_key


def require_role(*allowed_roles: str):
    def dependency(api_key: str = Depends(get_api_key)) -> str:
        role = get_role(api_key)
        if role is None:
            raise HTTPException(status_code=401, detail="invalid API key")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"role '{role}' not permitted")
        return role
    return dependency


@app.on_event("startup")
def seed_admin_key() -> None:
    admin_key = os.environ.get("ADMIN_API_KEY")
    if admin_key and not redis_client.hexists(RBAC_KEY_HASH, hash_key(admin_key)):
        redis_client.hset(RBAC_KEY_HASH, hash_key(admin_key), "admin")
        logger.info("seeded admin API key from ADMIN_API_KEY env var")


# --- LLM Guard scanner configuration -----------------------------------
# Every threshold below is a STARTING POINT, not a finished answer. Tune
# these against your own adversarial prompt set (the Kali VM is the right
# place to generate that set) and adjust based on what get logged as
# borderline or missed. Env vars let you retune without a rebuild.
#
# Known limitation worth internalizing: LLM Guard's PromptInjection
# scanner is a single classifier and has documented blind spots -- social-
# engineering-style jailbreaks phrased as harmless requests ("pretend
# you're my grandmother...") have been observed getting past it in
# real-world testing. Treat this scanner as one layer, not a guarantee --
# RBAC and output-side review still matter even with a well-tuned
# threshold here.

PROMPT_INJECTION_THRESHOLD = float(os.environ.get("PROMPT_INJECTION_THRESHOLD", "0.5"))
ANONYMIZE_THRESHOLD = float(os.environ.get("ANONYMIZE_THRESHOLD", "0.5"))
TOKEN_LIMIT = int(os.environ.get("TOKEN_LIMIT", "4096"))

# Log anything that scores within this margin of its threshold, even if it
# passed -- this is how you build the evidence to move a threshold with
# confidence later instead of guessing.
BORDERLINE_MARGIN = 0.15

vault = Vault()  # holds real values behind the placeholders Anonymize inserts

scanners = [
    # Order matters: catch injection/jailbreak attempts before anything
    # else processes the text.
    PromptInjection(threshold=PROMPT_INJECTION_THRESHOLD, match_type=MatchType.FULL),
    Anonymize(vault, threshold=ANONYMIZE_THRESHOLD),
    TokenLimit(limit=TOKEN_LIMIT),
]

SCANNER_THRESHOLDS = {
    "PromptInjection": PROMPT_INJECTION_THRESHOLD,
    "Anonymize": ANONYMIZE_THRESHOLD,
}


def log_borderline_scores(results_score: dict) -> None:
    for scanner_name, score in results_score.items():
        threshold = SCANNER_THRESHOLDS.get(scanner_name)
        if threshold is not None and abs(score - threshold) <= BORDERLINE_MARGIN:
            logger.warning(
                "borderline score for %s: %.3f (threshold %.3f)",
                scanner_name, score, threshold,
            )


def isolate_model_network() -> None:
    """SDN southbound action: disconnect the model container from every
    network it's on. This is the real circuit breaker, not just a logged
    rejection -- the container stays running but becomes unreachable."""
    container = docker_client.containers.get(MODEL_CONTAINER)
    networks = container.attrs["NetworkSettings"]["Networks"].keys()
    for net_name in list(networks):
        network = docker_client.networks.get(net_name)
        network.disconnect(container, force=True)
    logger.critical("isolated %s from all networks", MODEL_CONTAINER)


def check_rate_limit(identity: str) -> bool:
    """Fixed-window counter in Redis, keyed by API key hash rather than
    source IP -- multiple clients behind the same LAN IP get their own
    budget instead of sharing one."""
    key = f"ratelimit:{identity}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)
    return count <= RATE_LIMIT_MAX_REQUESTS


# --- continuous_control_plane wiring ------------------------------------
# Two honest limitations, not hidden ones:
#
# 1. Role vocabulary mismatch. RBAC only issues "admin" / "user" roles.
#    continuous_control_plane.py's rules for "engineer" and
#    "attacker_script" will never fire through this path as a result --
#    they're not wrong, they're just currently unreachable from here. If
#    you want those rules live, RBAC needs to actually issue those roles,
#    not just this function accepting them.
#
# 2. has_mfa is hardcoded False, not read from the request. Real MFA isn't
#    implemented anywhere in this project yet, and pulling "has_mfa" from
#    client-supplied JSON would let any caller simply claim they passed
#    MFA -- that's worse than not checking at all. Hardcoding False means
#    the "chat" action never trips the admin_access/MFA rule (it only
#    checks that rule for action == "admin_access"), so this is safe to
#    wire in now without breaking anything; it becomes meaningful once
#    real MFA verification exists and this gets replaced with a real
#    lookup.

def run_identity_policy_check(role: str, prompt: str) -> dict:
    return evaluate_control_plane_request(
        user_role=role,
        action="chat",
        has_mfa=False,  # TODO: replace with real MFA verification
        input_valid=bool(prompt),
    )


@app.post("/v1/chat")
async def chat(
    request: Request,
    api_key: str = Depends(get_api_key),
    role: str = Depends(require_role("admin", "user")),
):
    if not check_rate_limit(hash_key(api_key)):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    policy_result = run_identity_policy_check(role, prompt)
    logger.info("identity policy decision: %s (%s)", policy_result["decision"], policy_result["reason"])

    if policy_result["decision"] == "REJECT":
        raise HTTPException(status_code=403, detail=policy_result["reason"])
    if policy_result["decision"] == "ISOLATE":
        isolate_model_network()
        raise HTTPException(status_code=403, detail=policy_result["reason"])

    sanitized_prompt, results_valid, results_score = scan_prompt(scanners, prompt)
    log_borderline_scores(results_score)

    if not all(results_valid.values()):
        logger.warning("blocked prompt, scores=%s", results_score)
        isolate_model_network()
        raise HTTPException(
            status_code=403,
            detail={"blocked": True, "scores": results_score},
        )

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": body.get("model", DEFAULT_MODEL),
                "prompt": sanitized_prompt,
                "stream": False,
            },
        )
    return response.json()


class NewKeyRequest(BaseModel):
    role: str


@app.post("/v1/admin/keys")
async def create_api_key(body: NewKeyRequest, _: str = Depends(require_role("admin"))):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {VALID_ROLES}")
    new_key = secrets.token_urlsafe(32)
    redis_client.hset(RBAC_KEY_HASH, hash_key(new_key), body.role)
    logger.info("issued new '%s' API key", body.role)
    return {"api_key": new_key, "role": body.role}


@app.post("/v1/admin/reconnect")
async def reconnect_model(_: str = Depends(require_role("admin"))):
    """Manually reconnect the model container after an isolation trigger."""
    container = docker_client.containers.get(MODEL_CONTAINER)
    docker_client.networks.get(MODEL_NETWORK).connect(container)
    logger.info("reconnected %s to %s", MODEL_CONTAINER, MODEL_NETWORK)
    return {"status": "reconnected"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


   feat: wire continuous_control_plane identity check into chat endpoint

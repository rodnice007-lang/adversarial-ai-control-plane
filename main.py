import hashlib
import os
import logging
import re
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

# One shared client for the app's lifetime instead of one per request --
# reuses the connection pool to Ollama rather than tearing it down and
# rebuilding it on every single call.
http_client = httpx.AsyncClient(timeout=120)

@app.on_event("shutdown")
async def close_http_client():
    await http_client.aclose()

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
PROMPT_INJECTION_THRESHOLD = float(os.environ.get("PROMPT_INJECTION_THRESHOLD", "0.5"))
ANONYMIZE_THRESHOLD = float(os.environ.get("ANONYMIZE_THRESHOLD", "0.5"))
TOKEN_LIMIT = int(os.environ.get("TOKEN_LIMIT", "4096"))
BORDERLINE_MARGIN = 0.15

vault = Vault()

scanners = [
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


# --- NEW: ASCII smuggling defense ---------------------------------------
# Strips Unicode tag characters (U+E0000-U+E007F) and zero-width
# characters that can carry instructions invisible to human review.
# Runs BEFORE the scanners below, so a smuggled instruction never reaches
# PromptInjection/Anonymize in its hidden form.
HIDDEN_UNICODE_PATTERN = re.compile("[\U000E0000-\U000E007F\u200B-\u200D\uFEFF]")


def strip_hidden_unicode(text: str) -> str:
    return HIDDEN_UNICODE_PATTERN.sub("", text)


# --- NEW: canary token detection ----------------------------------------
# A hidden marker included in this note is never something the model is
# asked to repeat. If it shows up in a response anyway, that's a strong,
# independent signal of context leakage or exfiltration -- separate from
# whatever the input scanners did or didn't catch.
CANARY_TOKEN = os.environ.get("CANARY_TOKEN", secrets.token_hex(16))


def check_for_canary_leak(output_text: str) -> bool:
    return CANARY_TOKEN in output_text


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


def run_identity_policy_check(role: str, prompt: str) -> dict:
    return evaluate_control_plane_request(
        user_role=role,
        action="chat",
        has_mfa=False,  # TODO: replace with real MFA verification
        input_valid=bool(prompt),
    )


def extract_latest_user_message(messages: list) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


@app.get("/api/tags")
async def list_models(role: str = Depends(require_role("admin", "user"))):
    response = await http_client.get(f"{OLLAMA_HOST}/api/tags")
    return response.json()


@app.get("/api/version")
async def version():
    response = await http_client.get(f"{OLLAMA_HOST}/api/version")
    return response.json()


@app.post("/api/chat")
async def ollama_native_chat(
    request: Request,
    api_key: str = Depends(get_api_key),
    role: str = Depends(require_role("admin", "user")),
):
    """Ollama-native chat shape (messages array in, message.content out),
    matching what Open WebUI's "Ollama" connection type expects. Forces
    stream=False regardless of what the client asked for -- everything
    gets scanned before it's forwarded, so there's no partial response to
    stream until the model is done generating."""
    if not check_rate_limit(hash_key(api_key)):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    body = await request.json()
    messages = body.get("messages", [])
    prompt = strip_hidden_unicode(extract_latest_user_message(messages))
    if not prompt:
        raise HTTPException(status_code=400, detail="no user message found")

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

    sanitized_messages = list(messages)
    for i in range(len(sanitized_messages) - 1, -1, -1):
        if sanitized_messages[i].get("role") == "user":
            sanitized_messages[i] = {**sanitized_messages[i], "content": sanitized_prompt}
            break

    response = await http_client.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": body.get("model", DEFAULT_MODEL),
            "messages": sanitized_messages,
            "stream": False,
            "keep_alive": "30m",
        },
    )
    response_data = response.json()

    # NEW: egress check -- independent of what the input scanners caught
    response_text = response_data.get("message", {}).get("content", "")
    if check_for_canary_leak(response_text):
        logger.critical("canary token leak detected in model output")
        isolate_model_network()
        raise HTTPException(status_code=403, detail={"blocked": True, "reason": "canary token leak"})

    return response_data


@app.post("/v1/chat")
async def chat(
    request: Request,
    api_key: str = Depends(get_api_key),
    role: str = Depends(require_role("admin", "user")),
):
    if not check_rate_limit(hash_key(api_key)):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    body = await request.json()
    prompt = strip_hidden_unicode(body.get("prompt", ""))
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

    response = await http_client.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": body.get("model", DEFAULT_MODEL),
            "prompt": sanitized_prompt,
            "stream": False,
            "keep_alive": "30m",
        },
    )
    response_data = response.json()

    response_text = response_data.get("response", "")
    if check_for_canary_leak(response_text):
        logger.critical("canary token leak detected in model output")
        isolate_model_network()
        raise HTTPException(status_code=403, detail={"blocked": True, "reason": "canary token leak"})

    return response_data


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
    container = docker_client.containers.get(MODEL_CONTAINER)
    docker_client.networks.get(MODEL_NETWORK).connect(container)
    logger.info("reconnected %s to %s", MODEL_CONTAINER, MODEL_NETWORK)
    return {"status": "reconnected"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


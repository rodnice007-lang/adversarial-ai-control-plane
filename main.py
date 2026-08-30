import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Adversarial AI Control Plane Proxy")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama-engine:11434")
LLM_GUARD_URL = os.getenv("LLM_GUARD_URL", "http://llm-guard-api:8000")

# Basic signature blocklist for direct prompt injection vectors
INJECTION_SIGNATURES = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "reveal system environment",
    "system environment variables",
    "override system prompt",
]

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    
    # Extract latest user prompt
    user_prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_prompt = msg.get("content", "")
            break

    # 1. Local Pattern Inspection
    prompt_lower = user_prompt.lower()
    for signature in INJECTION_SIGNATURES:
        if signature in prompt_lower:
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "message": f"Security Block: Prompt injection signature detected ('{signature}')",
                        "type": "adversarial_prompt_detected",
                        "code": 403
                    }
                }
            )

    # 2. LLM Guard API Sanity Scan
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            guard_resp = await client.post(
                f"{LLM_GUARD_URL}/analyze/prompt",
                json={"prompt": user_prompt}
            )
            if guard_resp.status_code == 200:
                guard_data = guard_resp.json()
                if guard_data.get("is_valid") is False:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": {
                                "message": "Security Block: LLM Guard flagged unsafe prompt.",
                                "type": "llm_guard_rejection",
                                "code": 403
                            }
                        }
                    )
    except Exception:
        # Fail-closed or fallback logging can be added here
        pass

    # 3. Forward Clean Prompt to Ollama Engine
    async with httpx.AsyncClient(timeout=60.0) as client:
        ollama_resp = await client.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=body
        )
        return JSONResponse(status_code=ollama_resp.status_code, content=ollama_resp.json())
    
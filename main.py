import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Adversarial AI Control Plane Proxy")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama-engine:11434")

INJECTION_SIGNATURES = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "reveal system environment",
    "system environment variables",
    "override system prompt",
]


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    body: dict = await request.json()

    # 1. Inspect Prompt for Injections
    messages = body.get("messages", [])
    for msg in messages:
        content = str(msg.get("content", "")).lower()
        for signature in INJECTION_SIGNATURES:
            if signature in content:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "message": f"Security Block: Prompt injection signature detected ('{signature}')",
                            "type": "adversarial_prompt_detected",
                            "code": 403,
                        }
                    },
                )

    # 2. Forward Clean Prompt to Ollama Engine
    async with httpx.AsyncClient(timeout=60.0) as client:
        ollama_resp = await client.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=body,
        )
        response_data: dict = ollama_resp.json()
        return JSONResponse(
            status_code=ollama_resp.status_code,
            content=response_data,
        )
    
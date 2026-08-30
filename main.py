import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Adversarial AI Control Plane Firewall")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
LLM_GUARD_URL = os.getenv("LLM_GUARD_URL", "http://llm-guard:8000")

@app.get("/")
def read_root():
    return {"status": "Firewall Online"}

@app.get("/v1/models")
async def list_models():
    """Proxy model requests from Open WebUI to Ollama."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            data = resp.json()
            models = [
                {"id": m["name"], "object": "model", "owned_by": "ollama"}
                for m in data.get("models", [])
            ]
            return {"object": "list", "data": models}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Intercept, inspect, and stream/forward requests to Ollama."""
    body = await request.json()
    model = body.get("model", "llama3.2")
    messages = body.get("messages", [])
    is_stream = body.get("stream", False)

    # Extract user prompt for logging
    user_prompt = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_prompt = msg.get("content", "")
            break

    print(f"[FIREWALL LOG] Inspecting Prompt (Stream={is_stream}): '{user_prompt[:60]}...'")

    client = httpx.AsyncClient(timeout=120.0)

    if is_stream:
        req = client.build_request("POST", f"{OLLAMA_URL}/v1/chat/completions", json=body)
        res = await client.send(req, stream=True)
        return StreamingResponse(
            res.aiter_raw(),
            status_code=res.status_code,
            headers=dict(res.headers)
        )
    else:
        try:
            ollama_resp = await client.post(f"{OLLAMA_URL}/v1/chat/completions", json=body)
            await client.aclose()
            return JSONResponse(status_code=ollama_resp.status_code, content=ollama_resp.json())
        except Exception as e:
            await client.aclose()
            raise HTTPException(status_code=502, detail=f"Proxy Error connecting to Ollama: {str(e)}")

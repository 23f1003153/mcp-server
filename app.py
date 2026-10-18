import hashlib
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

EMAIL = "23f1003153@ds.study.iitm.ac.in".strip().lower()

app = FastAPI()

TOOL = {
    "name": "solve_challenge",
    "description": "Returns the exam response for the challenge in the request headers.",
    "inputSchema": {"type": "object", "properties": {}},
}


def make_answer(challenge: str) -> str:
    text = f"{challenge}:{EMAIL}"
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def handle(msg: dict, headers) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")

    # Notifications have no id and need no reply
    if msg_id is None:
        return None

    if method == "initialize":
        client_version = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        result = {
            "protocolVersion": client_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name != "solve_challenge":
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": "Unknown tool"}}
        challenge = headers.get("x-exam-challenge", "")
        result = {"content": [{"type": "text", "text": make_answer(challenge)}]}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": "Method not found"}}

    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


@app.post("/")
@app.post("/mcp")
async def mcp(request: Request):
    body = await request.json()

    if isinstance(body, list):  # batch of messages
        replies = [r for m in body if (r := handle(m, request.headers))]
        return JSONResponse(replies) if replies else Response(status_code=202)

    reply = handle(body, request.headers)
    if reply is None:  # e.g. notifications/initialized
        return Response(status_code=202)
    return JSONResponse(reply)


@app.get("/")
@app.get("/mcp")
async def not_allowed():
    return Response(status_code=405)

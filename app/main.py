from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app import ratelimit
from app.adapters.memory import MemoryAdapter
from app.agent.service import resolve_tool
from app.audit import logger
from app.models import AuditEntry, RunRequest, RunResponse
from app.tools import categorize as _categorize_reg  # noqa: F401 — registers tool
from app.tools import anomalies as _anomalies_reg  # noqa: F401
from app.tools import summary as _summary_reg  # noqa: F401
from app.tools.registry import execute

app = FastAPI(title="Xelsius", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

adapter = MemoryAdapter()


@app.post("/agent/run", response_model=RunResponse)
def agent_run(
    req: RunRequest,
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> RunResponse:
    user_key = x_api_key or req.api_key
    remaining: int | None = None

    if not user_key:
        ip = request.client.host if request.client else "unknown"
        allowed, remaining = ratelimit.check(ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Free tier limit reached. Provide your own API key to continue.",
            )

    # 1. Agent: resolve prompt → tool call
    try:
        tool_call = resolve_tool(req.prompt, user_api_key=user_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Tool: execute pure function → diff
    transactions = adapter.get_transactions()
    diff = execute(tool_call.tool, transactions, tool_call.args)

    # 3. Audit: log everything
    logger.record(
        prompt=req.prompt,
        tool=tool_call.tool.value,
        args=tool_call.args,
        diff=diff,
    )

    return RunResponse(
        tool=tool_call.tool.value,
        args=tool_call.args,
        diff=diff,
        remaining=remaining,
    )


@app.get("/audit/log", response_model=list[AuditEntry])
def audit_log() -> list[AuditEntry]:
    return logger.get_log()

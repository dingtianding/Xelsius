from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import ratelimit
from app.adapters.memory import MemoryAdapter
from app.agent.context import build_context
from app.agent.service import resolve_tool
from app.audit import logger
from app.ingest import data as ingest_data
from app.ingest import ocr as ingest_ocr
from app.models import (
    AuditEntry,
    ApplyRequest,
    ApplyResponse,
    DirectToolRequest,
    RunRequest,
    RunResponse,
    Transaction,
    UploadResponse,
    Workpaper,
)
from app.tools import categorize as _categorize_reg  # noqa: F401 — registers tool
from app.tools import anomalies as _anomalies_reg  # noqa: F401
from app.tools import summary as _summary_reg  # noqa: F401
from app.tools import reset as _reset_reg  # noqa: F401
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

    # 1. Build context + resolve prompt → tool call
    workpaper = adapter.get_workpaper()
    context = build_context(workpaper.transactions, logger.get_log())
    try:
        tool_call = resolve_tool(req.prompt, user_api_key=user_key, context=context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Tool: execute pure function → diff (reuse same workpaper snapshot)
    diff = execute(tool_call.tool, workpaper, tool_call.args)

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


@app.post("/tools/run", response_model=RunResponse)
def tools_run(req: DirectToolRequest) -> RunResponse:
    """Execute a tool directly — no AI, no rate limit. For preset buttons."""
    workpaper = adapter.get_workpaper()
    diff = execute(req.tool, workpaper, req.args)

    logger.record(
        prompt=f"[direct] {req.tool.value}",
        tool=req.tool.value,
        args=req.args,
        diff=diff,
    )

    return RunResponse(tool=req.tool.value, args=req.args, diff=diff)


@app.get("/transactions", response_model=list[Transaction])
def get_transactions() -> list[Transaction]:
    return adapter.get_transactions()


@app.get("/workpaper", response_model=Workpaper)
def get_workpaper() -> Workpaper:
    return adapter.get_workpaper()


@app.post("/agent/apply", response_model=ApplyResponse)
def agent_apply(req: ApplyRequest) -> ApplyResponse:
    adapter.apply_diff(req.diff)
    return ApplyResponse(transactions=adapter.get_transactions())


@app.post("/ingest/data", response_model=UploadResponse)
def ingest_data_file(file: UploadFile = File(...)) -> UploadResponse:
    """Parse a CSV or Excel file into transactions."""
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Missing content type")

    try:
        if file.content_type == "text/csv" or (file.filename and file.filename.endswith(".csv")):
            transactions = ingest_data.parse_csv(file.file)
        elif file.content_type in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ) or (file.filename and file.filename.endswith((".xlsx", ".xls"))):
            transactions = ingest_data.parse_excel(file.file)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Use CSV or Excel.",
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    adapter.load_transactions(transactions)
    return UploadResponse(transactions=transactions, count=len(transactions))


@app.post("/ingest/ocr", response_model=UploadResponse)
def ingest_ocr_file(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
) -> UploadResponse:
    """Extract transactions from an image or PDF via Claude vision."""
    content_type = file.content_type or ""
    if content_type not in ("image/png", "image/jpeg", "image/webp", "image/gif", "application/pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Use PNG, JPEG, WebP, GIF, or PDF.",
        )

    try:
        transactions = ingest_ocr.extract_transactions(
            file.file, content_type, user_api_key=x_api_key
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    adapter.load_transactions(transactions)
    return UploadResponse(transactions=transactions, count=len(transactions))


@app.get("/audit/log", response_model=list[AuditEntry])
def audit_log() -> list[AuditEntry]:
    return logger.get_log()

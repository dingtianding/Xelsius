import json

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app import ratelimit, sessions
from app.agent.context import build_context
from app.agent.providers import get_provider
from app.agent.service import resolve_tool
from app.agent.stream import run_agent_streaming
from app.ingest import data as ingest_data
from app.ingest import ocr as ingest_ocr
from app.agent.suggestions import generate_suggestions
from app.models import (
    AuditEntry,
    ApplyRequest,
    ApplyResponse,
    CellChange,
    CellEditRequest,
    CellEditResponse,
    DirectToolRequest,
    RunRequest,
    RunResponse,
    SuggestionsResponse,
    Transaction,
    UpdateCellsDiff,
    UploadResponse,
    Workpaper,
)
from app.tools import categorize as _categorize_reg  # noqa: F401 — registers tool
from app.tools import anomalies as _anomalies_reg  # noqa: F401
from app.tools import summary as _summary_reg  # noqa: F401
from app.tools import reset as _reset_reg  # noqa: F401
from app.tools import trial_balance as _tb_reg  # noqa: F401
from app.tools import materiality as _mat_reg  # noqa: F401
from app.tools import lead_sheet as _ls_reg  # noqa: F401
from app.tools import adjusting as _adj_reg  # noqa: F401
from app.tools import tickmarks as _tm_reg  # noqa: F401
from app.tools.registry import execute

app = FastAPI(title="Xelsius", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


def _get_session(session_id: str | None) -> tuple[str, sessions._Session]:
    return sessions.get_session(session_id)


# --- Session ---


@app.post("/session")
def create_session() -> dict:
    session_id = sessions.create_session()
    return {"session_id": session_id}


@app.get("/providers")
def list_providers() -> dict:
    """List available LLM providers and which keys are configured."""
    import os
    return {
        "default": get_provider(),
        "available": [
            {"id": "gemini", "name": "Gemini Flash", "free": True, "configured": bool(os.environ.get("GEMINI_API_KEY"))},
            {"id": "groq", "name": "Groq Llama", "free": True, "configured": bool(os.environ.get("GROQ_API_KEY"))},
            {"id": "anthropic", "name": "Claude Haiku", "free": False, "configured": bool(os.environ.get("ANTHROPIC_API_KEY"))},
        ],
    }


# --- Agent ---


@app.post("/agent/run", response_model=RunResponse)
def agent_run(
    req: RunRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> RunResponse:
    session_id, session = _get_session(x_session_id)
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

    workpaper = session.adapter.get_workpaper()
    context = build_context(workpaper, session.audit_log)
    try:
        tool_call = resolve_tool(req.prompt, user_api_key=user_key, context=context, provider=req.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    diff = execute(tool_call.tool, workpaper, tool_call.args)

    session.record(
        prompt=req.prompt,
        tool=tool_call.tool.value,
        args=tool_call.args,
        diff=diff,
    )

    resp = RunResponse(
        tool=tool_call.tool.value,
        args=tool_call.args,
        diff=diff,
        remaining=remaining,
    )
    response = JSONResponse(content=resp.model_dump())
    response.headers["x-session-id"] = session_id
    return response


# --- WebSocket: streaming agent ---


@app.websocket("/agent/ws")
async def agent_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")
            session_id = data.get("session_id")
            user_api_key = data.get("api_key")
            provider = data.get("provider")

            if not prompt:
                await websocket.send_json({"type": "error", "message": "Empty prompt"})
                continue

            sid, session = _get_session(session_id)

            # Send session ID back if it was created
            if sid != session_id:
                await websocket.send_json({"type": "session", "session_id": sid})

            workpaper = session.adapter.get_workpaper()

            async def on_step_async(event_type: str, step_data: dict):
                """Cannot be async in the sync callback, so we use a list to collect."""
                pass

            # Collect steps, then send — run_agent_streaming is sync
            steps: list[tuple[str, dict]] = []

            def on_step(event_type: str, step_data: dict):
                steps.append((event_type, step_data))

            try:
                tool_call, diff = run_agent_streaming(
                    prompt=prompt,
                    workpaper=workpaper,
                    audit_log=session.audit_log,
                    on_step=on_step,
                    user_api_key=user_api_key,
                    provider=provider,
                )

                # Send all steps
                for event_type, step_data in steps:
                    await websocket.send_json({"type": event_type, **step_data})

                # Record in session
                session.record(
                    prompt=prompt,
                    tool=tool_call.tool.value,
                    args=tool_call.args,
                    diff=diff,
                )

                # Send final result
                await websocket.send_json({
                    "type": "result",
                    "tool": tool_call.tool.value,
                    "args": tool_call.args,
                    "diff": json.loads(diff.model_dump_json()),
                    "session_id": sid,
                })

            except Exception as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})

    except WebSocketDisconnect:
        pass


# --- Direct tool execution ---


@app.post("/tools/run", response_model=RunResponse)
def tools_run(
    req: DirectToolRequest,
    x_session_id: str | None = Header(default=None),
) -> RunResponse:
    session_id, session = _get_session(x_session_id)
    workpaper = session.adapter.get_workpaper()
    diff = execute(req.tool, workpaper, req.args)

    session.record(
        prompt=f"[direct] {req.tool.value}",
        tool=req.tool.value,
        args=req.args,
        diff=diff,
    )

    resp = RunResponse(tool=req.tool.value, args=req.args, diff=diff)
    response = JSONResponse(content=resp.model_dump())
    response.headers["x-session-id"] = session_id
    return response


# --- Data access ---


@app.get("/transactions", response_model=list[Transaction])
def get_transactions(x_session_id: str | None = Header(default=None)) -> list[Transaction]:
    _, session = _get_session(x_session_id)
    return session.adapter.get_transactions()


@app.get("/workpaper", response_model=Workpaper)
def get_workpaper(x_session_id: str | None = Header(default=None)) -> Workpaper:
    _, session = _get_session(x_session_id)
    return session.adapter.get_workpaper()


@app.post("/cells/edit", response_model=CellEditResponse)
def cell_edit(
    req: CellEditRequest,
    x_session_id: str | None = Header(default=None),
) -> CellEditResponse:
    _, session = _get_session(x_session_id)
    transactions = session.adapter.get_transactions()

    if req.row < 0 or req.row >= len(transactions):
        raise HTTPException(status_code=400, detail=f"Row {req.row} out of range")

    txn = transactions[req.row]
    valid_columns = {"date", "description", "amount", "category"}
    if req.column not in valid_columns:
        raise HTTPException(status_code=400, detail=f"Invalid column: {req.column}")

    current_value = getattr(txn, req.column)
    if req.column == "amount":
        try:
            new_value: str | float = float(req.value)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Amount must be a number")
    else:
        new_value = str(req.value)

    change = CellChange(row=req.row, column=req.column, before=current_value, after=new_value)
    return CellEditResponse(diff=UpdateCellsDiff(changes=[change]))


@app.post("/agent/apply", response_model=ApplyResponse)
def agent_apply(
    req: ApplyRequest,
    x_session_id: str | None = Header(default=None),
) -> ApplyResponse:
    _, session = _get_session(x_session_id)
    session.adapter.apply_diff(req.diff)
    return ApplyResponse(transactions=session.adapter.get_transactions())


# --- Ingest ---


@app.post("/ingest/data", response_model=UploadResponse)
def ingest_data_file(
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None),
) -> UploadResponse:
    _, session = _get_session(x_session_id)

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

    session.adapter.load_transactions(transactions)
    return UploadResponse(transactions=transactions, count=len(transactions))


@app.post("/ingest/ocr", response_model=UploadResponse)
def ingest_ocr_file(
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> UploadResponse:
    _, session = _get_session(x_session_id)
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

    session.adapter.load_transactions(transactions)
    return UploadResponse(transactions=transactions, count=len(transactions))


# --- Suggestions ---


@app.get("/agent/suggestions", response_model=SuggestionsResponse)
def get_suggestions(
    x_session_id: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> SuggestionsResponse:
    _, session = _get_session(x_session_id)
    transactions = session.adapter.get_transactions()
    suggestions = generate_suggestions(transactions, user_api_key=x_api_key)
    return SuggestionsResponse(
        suggestions=[{"label": s["label"], "prompt": s["prompt"]} for s in suggestions]
    )


# --- Audit log ---


@app.get("/audit/log", response_model=list[AuditEntry])
def audit_log(x_session_id: str | None = Header(default=None)) -> list[AuditEntry]:
    _, session = _get_session(x_session_id)
    return session.audit_log

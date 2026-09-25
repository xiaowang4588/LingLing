from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from config import API_TOKEN, HOST, PORT
from fields import FORM_FIELD_ORDER, form_to_row_values, normalize_form_for_sheet, validate_form
from tencent_client import TencentDocClient, TencentDocError

app = FastAPI(
    title="腾讯文档报修填表服务",
    description="对接 qq-bot 报修表格，写入共享腾讯文档在线表格",
    version="0.1.0",
)


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN or API_TOKEN == "change-me":
        return
    expected = f"Bearer {API_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="无效的 API Token")


class RepairFormPayload(BaseModel):
    故障教室: str = ""
    报修时间: str = ""
    周次: str = ""
    报修类型: str = ""
    报修人: str = ""
    报修人学院: str = ""
    是否为外聘老师: str = "否"
    报修方式: str = ""
    处理人: str = ""
    是否更换设备: str = "否"
    处理情况: str = ""
    故障发生原因: str = ""
    处理方式: str = ""
    row: int | None = Field(default=None, description="指定行号；不传则自动递增")


class FillResponse(BaseModel):
    ok: bool
    dry_run: bool = False
    result: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)


class SyncRowResponse(BaseModel):
    ok: bool
    next_row: int


class RowStateResponse(BaseModel):
    ok: bool = True
    next_row: int
    data_start_row: int
    last_written_row: int | None = None
    updated_at: str | None = None
    note: str | None = None


class SetRowPayload(BaseModel):
    next_row: int = Field(..., ge=1, description="下一次写入的行号")
    note: str = Field(default="", description="备注，便于追溯手动调整")


client = TencentDocClient()


@app.get("/health")
async def health() -> dict[str, Any]:
    info = await client.health_info()
    return {"status": "ok", **info}


@app.get("/oauth/authorize-url")
async def oauth_authorize_url() -> dict[str, str]:
    try:
        return {"url": client.build_authorize_url()}
    except TencentDocError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(default=""),
) -> dict[str, Any]:
    try:
        token = await client.exchange_code(code)
    except TencentDocError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "state": state,
        "user_id": token.get("user_id"),
        "expires_in": token.get("expires_in"),
        "message": "授权成功，token 已写入 token.json",
    }


@app.post("/api/repair/fill", response_model=FillResponse, dependencies=[Depends(require_api_token)])
async def fill_repair_form(
    payload: RepairFormPayload,
    dry_run: bool = Query(default=False),
    sync_row: bool = Query(default=False, description="写入前导出表格同步下一行"),
) -> FillResponse:
    form = payload.model_dump(exclude={"row"})
    missing = validate_form(form)
    if missing:
        return FillResponse(ok=False, missing_fields=missing)

    if dry_run:
        book_id = client.book_id or "(待转换)"
        row = payload.row or client._read_next_row()
        normalized = normalize_form_for_sheet(form)
        return FillResponse(
            ok=True,
            dry_run=True,
            result={
                "book_id": book_id,
                "sheet_id": client.sheet_id,
                "row": row,
                "range": f"{client.sheet_id}!B{row}:N{row}",
                "values": form_to_row_values(normalized),
                "formatted": normalized,
            },
        )

    try:
        result = await client.append_form_row(
            form, row=payload.row, sync_row=sync_row
        )
    except TencentDocError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FillResponse(ok=True, result=result)


@app.post("/api/repair/sync-row", response_model=SyncRowResponse, dependencies=[Depends(require_api_token)])
async def sync_next_row() -> SyncRowResponse:
    try:
        next_row = await client.sync_next_row_from_export()
    except TencentDocError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SyncRowResponse(ok=True, next_row=next_row)


@app.get("/api/repair/row", response_model=RowStateResponse, dependencies=[Depends(require_api_token)])
async def get_repair_row() -> RowStateResponse:
    state = client.get_row_state()
    return RowStateResponse(**state)


@app.put("/api/repair/row", response_model=RowStateResponse, dependencies=[Depends(require_api_token)])
async def set_repair_row(payload: SetRowPayload) -> RowStateResponse:
    from config import DATA_START_ROW

    if payload.next_row < DATA_START_ROW:
        raise HTTPException(
            status_code=400,
            detail=f"next_row 不能小于数据起始行 {DATA_START_ROW}",
        )
    state = client.set_next_row(payload.next_row, note=payload.note or "manual_api")
    return RowStateResponse(**state)


@app.get("/api/repair/fields")
async def list_fields() -> dict[str, Any]:
    return {"fields": list(FORM_FIELD_ORDER)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)

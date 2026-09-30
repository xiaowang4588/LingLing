from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from config import API_TOKEN, HOST, PORT
from fields import FORM_FIELD_ORDER, form_to_row_values, normalize_form_for_sheet, validate_form
from tencent_client import TencentDocClient, TencentDocError
from token_refresh_scheduler import TokenRefreshScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 全局客户端和调度器
client = TencentDocClient()
token_scheduler = TokenRefreshScheduler(client, check_interval=3600, refresh_before_days=3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("腾讯文档填表服务启动中...")
    token_scheduler.start()
    logger.info("Token 自动刷新调度器已启动")
    yield
    # 关闭时
    logger.info("腾讯文档填表服务关闭中...")
    await token_scheduler.stop()
    logger.info("Token 自动刷新调度器已停止")


app = FastAPI(
    title="腾讯文档报修填表服务",
    description="对接 qq-bot 报修表格，写入共享腾讯文档在线表格",
    version="0.2.0",
    lifespan=lifespan,
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




@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        info = await client.health_info()
        logger.debug("健康检查成功")
        return {"status": "ok", **info}
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    logger.info(f"收到填表请求: 故障教室={form.get('故障教室', 'N/A')} dry_run={dry_run}")

    missing = validate_form(form)
    if missing:
        logger.warning(f"缺少必填字段: {missing}")
        return FillResponse(ok=False, missing_fields=missing)

    if dry_run:
        book_id = client.book_id or "(待转换)"
        row = payload.row or await client._read_next_row()
        normalized = normalize_form_for_sheet(form)
        logger.debug(f"预览模式: 将写入行号 {row}")
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
        logger.info(f"填表成功: 行号={result['row']}")
    except TencentDocError as exc:
        logger.error(f"腾讯文档API错误: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"填表异常: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return FillResponse(ok=True, result=result)


@app.post("/api/repair/sync-row", response_model=SyncRowResponse, dependencies=[Depends(require_api_token)])
async def sync_next_row() -> SyncRowResponse:
    logger.info("开始同步下一行行号（从导出）")
    try:
        next_row = await client.sync_next_row_from_export()
        logger.info(f"同步行号成功: next_row={next_row}")
    except TencentDocError as exc:
        logger.error(f"同步行号失败: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SyncRowResponse(ok=True, next_row=next_row)


@app.get("/api/repair/row", response_model=RowStateResponse, dependencies=[Depends(require_api_token)])
async def get_repair_row() -> RowStateResponse:
    logger.debug("查询当前行号状态")
    state = await client.get_row_state()
    return RowStateResponse(**state)


@app.put("/api/repair/row", response_model=RowStateResponse, dependencies=[Depends(require_api_token)])
async def set_repair_row(payload: SetRowPayload) -> RowStateResponse:
    from config import DATA_START_ROW

    logger.info(f"手动设置行号: next_row={payload.next_row} note={payload.note}")
    if payload.next_row < DATA_START_ROW:
        raise HTTPException(
            status_code=400,
            detail=f"next_row 不能小于数据起始行 {DATA_START_ROW}",
        )
    state = await client.set_next_row(payload.next_row, note=payload.note or "manual_api")
    return RowStateResponse(**state)


@app.get("/api/repair/fields")
async def list_fields() -> dict[str, Any]:
    return {"fields": list(FORM_FIELD_ORDER)}


@app.post("/api/repair/force-refresh-token")
async def force_refresh_token() -> dict[str, Any]:
    """手动触发 Token 刷新（调试用）"""
    logger.info("收到手动刷新 Token 请求")
    success = await token_scheduler.force_refresh()
    if success:
        return {"ok": True, "message": "Token 刷新成功"}
    else:
        raise HTTPException(status_code=500, detail="Token 刷新失败，请检查日志")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)

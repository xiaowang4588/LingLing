from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import httpx

from config import (
    DATA_START_ROW,
    OAUTH_BASE,
    OPENAPI_BASE,
    ROW_STATE_FILE,
    SYNC_ROW_BEFORE_FILL,
    TENCENT_DOC_ACCESS_TOKEN,
    TENCENT_DOC_BOOK_ID,
    TENCENT_DOC_CLIENT_ID,
    TENCENT_DOC_CLIENT_SECRET,
    TENCENT_DOC_ENCODED_ID,
    TENCENT_DOC_OPEN_ID,
    TENCENT_DOC_REDIRECT_URI,
    TENCENT_DOC_REFRESH_TOKEN,
    TENCENT_DOC_SHEET_ID,
    TENCENT_DOC_SHEET_URL,
    TOKEN_FILE,
)
from fields import FORM_FIELD_ORDER, build_write_range, form_to_row_values


class TencentDocError(Exception):
    def __init__(self, message: str, *, ret: int | None = None, payload: Any = None):
        super().__init__(message)
        self.ret = ret
        self.payload = payload


class TencentDocClient:
    """腾讯文档在线表格 OpenAPI 客户端（官方 HTTPS 接口）。"""

    def __init__(self) -> None:
        self.client_id = TENCENT_DOC_CLIENT_ID
        self.client_secret = TENCENT_DOC_CLIENT_SECRET
        self.redirect_uri = TENCENT_DOC_REDIRECT_URI
        self.access_token = TENCENT_DOC_ACCESS_TOKEN
        self.refresh_token = TENCENT_DOC_REFRESH_TOKEN
        self.open_id = TENCENT_DOC_OPEN_ID
        self.book_id = TENCENT_DOC_BOOK_ID
        self.sheet_id = TENCENT_DOC_SHEET_ID
        self.encoded_id = TENCENT_DOC_ENCODED_ID
        self._load_token_file()

    def _load_token_file(self) -> None:
        if not TOKEN_FILE.is_file():
            return
        try:
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.access_token = data.get("access_token") or self.access_token
        self.refresh_token = data.get("refresh_token") or self.refresh_token
        self.open_id = data.get("open_id") or self.open_id
        if data.get("book_id"):
            self.book_id = data["book_id"]

    def _save_token_file(self) -> None:
        payload = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "open_id": self.open_id,
            "book_id": self.book_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        TOKEN_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def parse_sheet_url(url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        encoded_id = parts[-1] if parts else ""
        tab = parse_qs(parsed.query).get("tab", [""])[0]
        return encoded_id, tab

    def auth_headers(self) -> dict[str, str]:
        if not (self.access_token and self.client_id and self.open_id):
            raise TencentDocError(
                "未配置腾讯文档 OAuth：需要 access_token、client_id、open_id。"
                "请访问 /oauth/authorize-url 完成授权。"
            )
        return {
            "Access-Token": self.access_token,
            "Client-Id": self.client_id,
            "Open-Id": self.open_id,
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
        retry_on_auth: bool = True,
    ) -> dict[str, Any]:
        url = f"{OPENAPI_BASE}{path}"
        headers = {**self.auth_headers(), "Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
            )
        if resp.status_code == 401 and retry_on_auth and self.refresh_token:
            await self.refresh_access_token()
            return await self._request(
                method, path, params=params, json_body=json_body, retry_on_auth=False
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise TencentDocError(
                f"腾讯文档响应非 JSON: HTTP {resp.status_code} {resp.text[:200]}"
            ) from exc
        if isinstance(data, str):
            data = json.loads(data.replace("'", '"'))
        ret = data.get("ret")
        if ret not in (0, None):
            raise TencentDocError(
                data.get("msg") or "腾讯文档 API 错误",
                ret=ret,
                payload=data,
            )
        if resp.status_code >= 400:
            raise TencentDocError(
                f"HTTP {resp.status_code}: {data.get('msg') or resp.text[:200]}",
                payload=data,
            )
        return data

    def build_authorize_url(self, state: str = "repair-form") -> str:
        if not self.client_id:
            raise TencentDocError("未配置 TENCENT_DOC_CLIENT_ID")
        params = (
            f"client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            "&response_type=code"
            "&scope=all"
            f"&state={state}"
        )
        return f"{OAUTH_BASE}/authorize?{params}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        if not (self.client_id and self.client_secret):
            raise TencentDocError("未配置 client_id / client_secret")
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code": code,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{OAUTH_BASE}/token", params=params)
        data = resp.json()
        if resp.status_code >= 400 or "access_token" not in data:
            raise TencentDocError(f"换取 token 失败: {data}")
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token") or self.refresh_token
        self.open_id = data.get("user_id") or self.open_id
        self._save_token_file()
        return data

    async def refresh_access_token(self) -> dict[str, Any]:
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise TencentDocError("无法刷新 token：缺少 client 或 refresh_token")
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{OAUTH_BASE}/token", params=params)
        data = resp.json()
        if resp.status_code >= 400 or "access_token" not in data:
            raise TencentDocError(f"刷新 token 失败: {data}")
        self.access_token = data["access_token"]
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]
        if data.get("user_id"):
            self.open_id = data["user_id"]
        self._save_token_file()
        return data

    async def ensure_book_id(self) -> str:
        if self.book_id:
            return self.book_id
        encoded_id = self.encoded_id
        if not encoded_id and TENCENT_DOC_SHEET_URL:
            encoded_id, tab = self.parse_sheet_url(TENCENT_DOC_SHEET_URL)
            if tab:
                self.sheet_id = tab
        if not encoded_id:
            raise TencentDocError("未配置表格 encodedID")
        data = await self._request(
            "GET",
            "/drive/v2/util/converter",
            params={"type": 2, "value": encoded_id},
        )
        book_id = (data.get("data") or {}).get("fileID") or (data.get("data") or {}).get(
            "fileId"
        )
        if not book_id:
            raise TencentDocError("fileID 转换失败", payload=data)
        self.book_id = book_id
        self._save_token_file()
        return book_id

    @staticmethod
    def _sheet_path(book_id: str, suffix: str) -> str:
        return f"/sheetbook/v2/{quote(book_id, safe='')}/{suffix.lstrip('/')}"

    @staticmethod
    def _values_path(book_id: str, range_a1: str) -> str:
        # range 仅编码 !，避免 quote 整段导致列偏移
        safe_book = quote(book_id, safe="")
        safe_range = range_a1.replace("!", "%21")
        return f"/sheetbook/v2/{safe_book}/values/{safe_range}"

    def _read_row_state(self) -> dict[str, Any]:
        if ROW_STATE_FILE.is_file():
            try:
                data = json.loads(ROW_STATE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def _read_next_row(self) -> int:
        state = self._read_row_state()
        try:
            row = int(state.get("next_row", DATA_START_ROW))
        except (TypeError, ValueError):
            row = DATA_START_ROW
        return max(row, DATA_START_ROW)

    def _write_next_row(
        self,
        row: int,
        *,
        last_written_row: int | None = None,
        note: str | None = None,
    ) -> None:
        row = max(int(row), DATA_START_ROW)
        state = self._read_row_state()
        state["next_row"] = row
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        if last_written_row is not None:
            state["last_written_row"] = last_written_row
        if note:
            state["note"] = note
        ROW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ROW_STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def set_next_row(self, row: int, *, note: str = "") -> dict[str, Any]:
        """手动设置下一次写入行号（不小于 DATA_START_ROW）。"""
        self._write_next_row(row, note=note or "manual")
        return self.get_row_state()

    def get_row_state(self) -> dict[str, Any]:
        state = self._read_row_state()
        return {
            "next_row": self._read_next_row(),
            "data_start_row": DATA_START_ROW,
            "last_written_row": state.get("last_written_row"),
            "updated_at": state.get("updated_at"),
            "note": state.get("note"),
        }

    async def sync_next_row_from_export(self) -> int:
        """导出 xlsx 解析最后一行（每日限次，仅在必要时调用）。"""
        import io

        import openpyxl

        book_id = await self.ensure_book_id()
        export_path = f"/drive/v2/files/{quote(book_id, safe='')}/async-export"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{OPENAPI_BASE}{export_path}",
                headers={
                    **self.auth_headers(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"exportType": "sheet"},
            )
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(body, str):
            body = json.loads(body.replace("'", '"'))
        op = (body.get("data") or {}).get("operationID")
        if not op:
            raise TencentDocError("导出失败", payload=body)
        prog_path = f"/drive/v2/files/{quote(book_id, safe='')}/export-progress"
        url = None
        for _ in range(40):
            await asyncio.sleep(2)
            data = await self._request("GET", prog_path, params={"operationID": op})
            url = (data.get("data") or {}).get("url")
            if url:
                break
        if not url:
            raise TencentDocError("导出超时")
        async with httpx.AsyncClient(timeout=120.0) as client:
            xlsx = await client.get(url)
        wb = openpyxl.load_workbook(io.BytesIO(xlsx.content), read_only=True, data_only=True)
        sh = wb.active
        next_row = DATA_START_ROW
        last_with_data = DATA_START_ROW - 1
        for i, row in enumerate(
            sh.iter_rows(min_row=DATA_START_ROW, max_col=2, values_only=True),
            start=DATA_START_ROW,
        ):
            classroom = row[1] if len(row) > 1 else None
            has_b = classroom is not None and str(classroom).strip()
            if has_b:
                last_with_data = i
            elif next_row == DATA_START_ROW or i < next_row:
                # 首个 B 列为空的行（A 列可能已有序号）
                next_row = i
        if last_with_data >= DATA_START_ROW:
            candidate = last_with_data + 1
            # 若末行之后 B 已空则优先用上面找到的首个空行
            if next_row <= last_with_data:
                pass
            else:
                next_row = candidate
        self._write_next_row(next_row, note="sync_export")
        return next_row

    async def _maybe_sync_next_row(self, *, force: bool = False) -> None:
        if not force and not SYNC_ROW_BEFORE_FILL:
            return
        if self._read_next_row() >= DATA_START_ROW and not force:
            return
        try:
            await self.sync_next_row_from_export()
        except TencentDocError:
            pass

    async def append_form_row(
        self,
        form: dict[str, str],
        *,
        row: int | None = None,
        sync_row: bool = False,
    ) -> dict[str, Any]:
        book_id = await self.ensure_book_id()
        if sync_row:
            try:
                await self.sync_next_row_from_export()
            except TencentDocError:
                await self._maybe_sync_next_row(force=False)
        elif row is None:
            await self._maybe_sync_next_row(force=False)

        target_row = row or self._read_next_row()
        if target_row < DATA_START_ROW:
            target_row = DATA_START_ROW

        row_values = form_to_row_values(form)
        range_a1 = build_write_range(self.sheet_id, target_row)
        payload = {"values": [row_values]}
        await self._request(
            "PUT",
            self._values_path(book_id, range_a1),
            json_body=payload,
        )
        if row is None:
            self._write_next_row(target_row + 1, last_written_row=target_row, note="auto_after_fill")
        return {
            "book_id": book_id,
            "sheet_id": self.sheet_id,
            "range": range_a1,
            "row": target_row,
            "columns": "B:N",
            "value_count": len(row_values),
            "values": row_values,
            "formatted": dict(zip(FORM_FIELD_ORDER, row_values, strict=True)),
        }

    async def health_info(self) -> dict[str, Any]:
        encoded_id, tab = self.parse_sheet_url(TENCENT_DOC_SHEET_URL)
        return {
            "configured": bool(self.client_id and self.access_token and self.open_id),
            "has_refresh_token": bool(self.refresh_token),
            "book_id": self.book_id or None,
            "encoded_id": encoded_id or self.encoded_id,
            "sheet_id": tab or self.sheet_id,
            "data_start_row": DATA_START_ROW,
            "next_row": self._read_next_row(),
            "row_state": self.get_row_state(),
            "fields": list(FORM_FIELD_ORDER),
        }

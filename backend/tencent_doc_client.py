"""后台管理系统调用腾讯文档填表服务的客户端"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TencentDocFillerClient:
    """腾讯文档填表服务客户端

    后台管理系统通过此客户端与 tencent-doc-filler 服务通信
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8090",
        api_token: str = "change-me",
        timeout: float = 30.0,
    ):
        """
        Args:
            base_url: tencent-doc-filler 服务地址
            api_token: API 认证 Token
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        """生成请求头"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def submit_repair_form(
        self,
        form_data: dict[str, str],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """提交报修工单到腾讯文档

        Args:
            form_data: 报修表单数据（包含所有必填字段）
            dry_run: 是否为预览模式（不实际写入）

        Returns:
            API 响应结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 响应数据格式错误
        """
        url = f"{self.base_url}/api/repair/fill"
        params = {"dry_run": str(dry_run).lower()}

        logger.info(
            f"提交腾讯文档填表: 故障教室={form_data.get('故障教室', 'N/A')} "
            f"dry_run={dry_run}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                params=params,
                json=form_data,
            )
            response.raise_for_status()
            result = response.json()

        if not result.get("ok"):
            missing_fields = result.get("missing_fields", [])
            logger.warning(f"腾讯文档填表失败，缺少字段: {missing_fields}")
            raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

        logger.info(
            f"腾讯文档填表成功: 行号={result.get('result', {}).get('row', 'N/A')}"
        )
        return result

    async def check_health(self) -> dict[str, Any]:
        """检查腾讯文档服务健康状态

        Returns:
            服务健康状态信息
        """
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"腾讯文档服务健康检查失败: {e}")
            return {"status": "error", "message": str(e)}

    async def get_next_row(self) -> int | None:
        """获取下一行写入行号

        Returns:
            下一行行号，失败返回 None
        """
        url = f"{self.base_url}/api/repair/row"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=self._headers())
                response.raise_for_status()
                result = response.json()
                return result.get("next_row")
        except Exception as e:
            logger.error(f"获取行号失败: {e}")
            return None

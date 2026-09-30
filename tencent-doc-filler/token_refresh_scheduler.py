"""Token 自动刷新调度器 - 定期检查并刷新 Access Token"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import TOKEN_FILE
from tencent_client import TencentDocClient, TencentDocError

logger = logging.getLogger(__name__)


class TokenRefreshScheduler:
    """Token 自动刷新调度器

    定期检查 Access Token 的有效期，在过期前自动刷新。
    默认在 Token 过期前 3 天开始尝试刷新。
    """

    def __init__(
        self,
        client: TencentDocClient,
        check_interval: int = 3600,  # 每小时检查一次
        refresh_before_days: int = 3,  # 过期前3天刷新
    ):
        """
        Args:
            client: 腾讯文档客户端实例
            check_interval: 检查间隔（秒）
            refresh_before_days: 提前多少天刷新 Token
        """
        self.client = client
        self.check_interval = check_interval
        self.refresh_before_days = refresh_before_days
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning("Token 刷新调度器已在运行")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"Token 刷新调度器已启动 (检查间隔={self.check_interval}s, "
            f"提前刷新={self.refresh_before_days}天)"
        )

    async def stop(self) -> None:
        """停止调度器"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Token 刷新调度器已停止")

    async def _run(self) -> None:
        """调度器主循环"""
        while self._running:
            try:
                await self._check_and_refresh()
            except Exception as e:
                logger.error(f"Token 检查刷新失败: {e}")

            # 等待下一次检查
            await asyncio.sleep(self.check_interval)

    async def _check_and_refresh(self) -> None:
        """检查并刷新 Token"""
        # 检查是否有 refresh_token
        if not self.client.refresh_token:
            logger.debug("未配置 refresh_token，跳过自动刷新")
            return

        # 解析 Token 过期时间
        expire_time = self._parse_token_expiry(self.client.access_token)
        if not expire_time:
            logger.warning("无法解析 Access Token 过期时间")
            return

        now = datetime.now(timezone.utc)
        time_remaining = expire_time - now

        logger.debug(
            f"Token 剩余有效期: {time_remaining.days}天 "
            f"{time_remaining.seconds // 3600}小时"
        )

        # 判断是否需要刷新
        refresh_threshold = timedelta(days=self.refresh_before_days)
        if time_remaining > refresh_threshold:
            logger.debug("Token 仍在有效期内，无需刷新")
            return

        # 执行刷新
        logger.info(
            f"Token 即将过期（剩余 {time_remaining.days}天），开始自动刷新"
        )
        try:
            result = await self.client.refresh_access_token()
            logger.info(
                f"Token 自动刷新成功，新 Token 有效期: "
                f"{result.get('expires_in', 'N/A')}秒"
            )

            # 刷新后重新解析过期时间
            new_expire_time = self._parse_token_expiry(self.client.access_token)
            if new_expire_time:
                logger.info(
                    f"新 Token 将于 {new_expire_time.strftime('%Y-%m-%d %H:%M:%S UTC')} 过期"
                )

        except TencentDocError as e:
            logger.error(f"Token 自动刷新失败: {e}")
            # 可以在这里添加告警通知

    @staticmethod
    def _parse_token_expiry(access_token: str) -> datetime | None:
        """解析 JWT Token 的过期时间

        Args:
            access_token: JWT Access Token

        Returns:
            过期时间（UTC），解析失败返回 None
        """
        if not access_token:
            return None

        try:
            import base64

            # JWT 格式: header.payload.signature
            parts = access_token.split(".")
            if len(parts) != 3:
                return None

            # 解码 payload（Base64URL）
            payload_b64 = parts[1]
            # 补齐 padding
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload_json = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_json)

            # 获取过期时间戳
            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                return None

            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        except Exception as e:
            logger.warning(f"解析 Token 过期时间失败: {e}")
            return None

    async def force_refresh(self) -> bool:
        """手动触发立即刷新

        Returns:
            是否刷新成功
        """
        if not self.client.refresh_token:
            logger.error("未配置 refresh_token，无法刷新")
            return False

        try:
            logger.info("手动触发 Token 刷新")
            await self.client.refresh_access_token()
            logger.info("Token 手动刷新成功")
            return True
        except TencentDocError as e:
            logger.error(f"Token 手动刷新失败: {e}")
            return False

"""本地/服务器试用：dry-run 校验示例报修数据。"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

SAMPLE = {
    "故障教室": "勤者楼409",
    "报修时间": "2026-06-07",
    "周次": "第14周",
    "报修类型": "话筒",
    "报修人": "刘红",
    "报修人学院": "马克思主义学院",
    "是否为外聘老师": "否",
    "报修方式": "多媒体报修群",
    "处理人": "黄秀容",
    "是否更换设备": "是",
    "处理情况": "已处理",
    "故障发生原因": "话筒损坏",
    "处理方式": "更换话筒已解决",
}

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ""


async def main() -> None:
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        health = await client.get(f"{BASE}/health")
        print("health:", health.status_code, health.text)

        dry = await client.post(
            f"{BASE}/api/repair/fill?dry_run=true",
            json=SAMPLE,
            headers=headers,
        )
        print("dry_run:", dry.status_code)
        print(json.dumps(dry.json(), ensure_ascii=False, indent=2))

        real = await client.post(
            f"{BASE}/api/repair/fill",
            json=SAMPLE,
            headers=headers,
        )
        print("fill:", real.status_code)
        print(json.dumps(real.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

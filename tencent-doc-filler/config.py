from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# 服务
HOST = os.getenv("TENCENT_DOC_FILLER_HOST", "127.0.0.1")
PORT = int(os.getenv("TENCENT_DOC_FILLER_PORT", "8090") or "8090")
API_TOKEN = os.getenv("TENCENT_DOC_FILLER_API_TOKEN", "").strip()

# 腾讯文档 OAuth（开放平台 https://docs.qq.com/open/document/app/get_started.html）
TENCENT_DOC_CLIENT_ID = os.getenv("TENCENT_DOC_CLIENT_ID", "").strip()
TENCENT_DOC_CLIENT_SECRET = os.getenv("TENCENT_DOC_CLIENT_SECRET", "").strip()
TENCENT_DOC_REDIRECT_URI = os.getenv(
    "TENCENT_DOC_REDIRECT_URI", "https://docs.qq.com"
).strip()
TENCENT_DOC_ACCESS_TOKEN = os.getenv("TENCENT_DOC_ACCESS_TOKEN", "").strip()
TENCENT_DOC_REFRESH_TOKEN = os.getenv("TENCENT_DOC_REFRESH_TOKEN", "").strip()
TENCENT_DOC_OPEN_ID = os.getenv("TENCENT_DOC_OPEN_ID", "").strip()

TOKEN_FILE = Path(
    os.getenv("TENCENT_DOC_TOKEN_FILE", str(BASE_DIR / "token.json"))
)

# 目标表格（默认：綦江校区设备报修表）
TENCENT_DOC_SHEET_URL = os.getenv(
    "TENCENT_DOC_SHEET_URL",
    "https://docs.qq.com/sheet/DV0toQUhZZXBlS29R?tab=BB08J2",
).strip()
TENCENT_DOC_ENCODED_ID = os.getenv("TENCENT_DOC_ENCODED_ID", "DV0toQUhZZXBlS29R").strip()
TENCENT_DOC_SHEET_ID = os.getenv("TENCENT_DOC_SHEET_ID", "BB08J2").strip()
TENCENT_DOC_BOOK_ID = os.getenv("TENCENT_DOC_BOOK_ID", "").strip()

# 数据区起始行：此前为第 3 行；现从第 484 行起追加（A 列序号由表格自带）
DATA_START_ROW = int(os.getenv("TENCENT_DOC_DATA_START_ROW", "484") or "484")
ROW_STATE_FILE = Path(
    os.getenv("TENCENT_DOC_ROW_STATE_FILE", str(BASE_DIR / "next_row.json"))
)
# 写入前是否导出表格同步下一行（每日限 9 次；默认关闭，改用手动 next_row.json）
SYNC_ROW_BEFORE_FILL = os.getenv("TENCENT_DOC_SYNC_BEFORE_FILL", "false").strip().lower() in (
    "1", "true", "yes", "on",
)

OAUTH_BASE = "https://docs.qq.com/oauth/v2"
OPENAPI_BASE = "https://docs.qq.com/openapi"

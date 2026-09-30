# 腾讯文档 OpenAPI Token 自动获取与续期：实现说明与复用指南

本文说明本项目（`tencent-doc-filler`）如何获取并自动续期腾讯文档 OpenAPI 的 Access Token，代码分别在哪里，以及如何把这套机制移植到你自己的项目中。

---

## 1. 先说清楚：哪些能自动，哪些不能

| 环节 | 能否自动 | 说明 |
|------|----------|------|
| 首次授权（用户点“同意”） | ❌ 不能 | OAuth2 授权码模式要求 **表格所有者本人在浏览器里登录并同意一次**，这是腾讯文档的安全设计，任何代码都绕不过去 |
| 授权码 `code` → Token | ✅ 可以 | 配好回调地址后可全自动；本项目当前用的是“手动复制 code”方式（见第 5 节） |
| Access Token 到期前续期 | ✅ 可以 | 前提是手里有 `refresh_token` |
| 调用 API 时遇 401 自动刷新重试 | ✅ 可以 | 同上 |
| `refresh_token` 本身失效后 | ❌ 不能 | 只能重新走一次首次授权 |

> ⚠️ **本项目当前状态**：服务器上的 `token.json` 中 `refresh_token` 为空，所以自动续期**目前不会生效**。Access Token 到期（30 天）后仍需人工重新授权。按第 5 节重新授权一次，并确认 `/health` 返回 `"has_refresh_token": true` 之后，自动续期才会启用。

---

## 2. 官方接口依据

| 项目 | 内容 | 核实情况 |
|------|------|----------|
| 授权页 | `GET https://docs.qq.com/oauth/v2/authorize?client_id=&redirect_uri=&response_type=code&scope=all&state=` | ✅ 官方文档 |
| code 有效期 | 5 分钟，一次性 | ✅ 官方文档 |
| 换取 Token | `GET https://docs.qq.com/oauth/v2/token?client_id=&client_secret=&redirect_uri=&grant_type=authorization_code&code=` | ✅ 官方文档 |
| 返回字段 | `access_token`、`refresh_token`、`expires_in`（2592000 秒 = 30 天）、`user_id`（即 Open ID）、`scope`、`token_type` | ✅ 官方文档示例 |
| 调用 API 鉴权头 | `Access-Token`、`Client-Id`、`Open-Id` 三个 Header | ✅ 官方文档 |
| 刷新 Token | `GET https://docs.qq.com/oauth/v2/token?client_id=&client_secret=&grant_type=refresh_token&refresh_token=` | ⚠️ 未核实，按标准 OAuth2 写法推断，本项目代码也是这样实现的 |
| refresh_token 有效期 / 刷新后是否换新 | 未知 | ⚠️ 未核实，代码按“返回了新的就替换，没返回就沿用旧的”处理 |

官方文档入口：
- 接入教程：https://docs.qq.com/open/document/app/get_started.html
- 授权（OAuth2）：https://docs.qq.com/open/document/app/oauth2/

**建议**：上线前到“授权 → 刷新 Token”页面核对刷新接口的参数和 refresh_token 的有效期，若与上表不同，只需改 `refresh_access_token()` 一个函数。

---

## 3. 代码出处（本项目内）

所有代码都在 `tencent-doc-filler/` 目录，服务器路径为 `/www/wwwroot/tencent-doc-filler/`。

| 功能 | 文件 | 函数 / 类 |
|------|------|-----------|
| 读取配置（client_id、secret 等） | [config.py](tencent-doc-filler/config.py) | 模块级常量 |
| 生成授权链接 | [tencent_client.py](tencent-doc-filler/tencent_client.py) | `TencentDocClient.build_authorize_url()` |
| code 换 Token 并落盘 | [tencent_client.py](tencent-doc-filler/tencent_client.py) | `TencentDocClient.exchange_code()` |
| 刷新 Token | [tencent_client.py](tencent-doc-filler/tencent_client.py) | `TencentDocClient.refresh_access_token()` |
| 401 自动刷新并重试 | [tencent_client.py](tencent-doc-filler/tencent_client.py) | `TencentDocClient._request()` |
| Token 读写（带文件锁） | [tencent_client.py](tencent-doc-filler/tencent_client.py) | `_load_token_file()` / `_save_token_file()` |
| 跨进程文件锁 | [file_lock.py](tencent-doc-filler/file_lock.py) | `FileLock`、`safe_write_json()` |
| 到期前定时续期 | [token_refresh_scheduler.py](tencent-doc-filler/token_refresh_scheduler.py) | `TokenRefreshScheduler` |
| HTTP 入口 | [app.py](tencent-doc-filler/app.py) | `/oauth/authorize-url`、`/oauth/callback`、`/api/repair/force-refresh-token` |

Token 按以下优先级加载：`token.json` 中的值 > `.env` 中的值。每次换取或刷新成功后都会写回 `token.json`。

---

## 4. 工作流程

```
            ┌────────────── 首次（人工，一次） ──────────────┐
            │ 1. GET /oauth/authorize-url  → 得到授权链接     │
            │ 2. 表格所有者在浏览器打开并点“同意”            │
            │ 3. 浏览器跳转到 redirect_uri?code=xxx           │
            │ 4. GET /oauth/callback?code=xxx                 │
            │    → exchange_code() → 写入 token.json          │
            └─────────────────────────────────────────────────┘
                                  │
            ┌────────────── 之后（全自动） ──────────────────┐
            │ A. TokenRefreshScheduler 每小时检查一次          │
            │    解析 access_token（JWT）里的 exp 字段         │
            │    剩余 < 3 天 → refresh_access_token()          │
            │ B. 任意 API 返回 401                             │
            │    → refresh_access_token() → 原请求重试一次     │
            └─────────────────────────────────────────────────┘
```

说明：当前腾讯文档签发的 access_token 是 JWT 格式，payload 中含 `exp`（过期时间戳），所以调度器可以离线计算剩余有效期，不必额外调接口。如果以后格式变了、解析不出 `exp`，调度器会打日志跳过，但 **B（401 兜底）仍然有效**。

---

## 5. 首次授权操作步骤

### 方式一：手动复制 code（本项目当前做法）

`.env` 中 `TENCENT_DOC_REDIRECT_URI=https://docs.qq.com`，授权后会跳到腾讯文档首页，code 在地址栏里。

```bash
# 1. 获取授权链接
curl -s http://127.0.0.1:8090/oauth/authorize-url

# 2. 用表格所有者的 QQ 在浏览器打开链接 → 同意
# 3. 从地址栏复制 code=... 的值（5 分钟内有效，只能用一次）

# 4. 换取 Token
curl "http://127.0.0.1:8090/oauth/callback?code=粘贴code&state=repair-form"

# 5. 确认拿到了 refresh_token
curl -s http://127.0.0.1:8090/health | grep has_refresh_token
```

### 方式二：回调地址全自动接收 code（推荐）

服务里已经有 `/oauth/callback` 路由，只需让腾讯能访问到它：

1. 在 Nginx 中把一个公网 HTTPS 地址反代到本服务：
   ```nginx
   location /tdoc/oauth/callback {
       proxy_pass http://127.0.0.1:8090/oauth/callback;
   }
   ```
2. 在腾讯文档开放平台的应用设置中，把回调地址登记为 `https://你的域名/tdoc/oauth/callback`。
3. 修改 `.env`：`TENCENT_DOC_REDIRECT_URI=https://你的域名/tdoc/oauth/callback`，重启服务。

之后用户点“同意”，浏览器会直接请求回调地址，Token 自动写入 `token.json`，无需复制 code。

> ⚠️ 回调地址暴露到公网后，建议校验 `state` 参数（目前代码只是原样返回，没有校验），防止他人伪造回调。

---

## 6. 移植到你自己的项目

### 方案 A：直接复用本服务（最省事）

把 `tencent-doc-filler` 当作独立的“腾讯文档网关”部署，你的项目通过 HTTP 调用，完全不用碰 Token：

```bash
curl -X POST http://127.0.0.1:8090/api/repair/fill \
  -H "Authorization: Bearer <TENCENT_DOC_FILLER_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"故障教室": "...", ...}'
```

缺点：接口是为“报修表 B~N 列”定制的。如需写其他表，要改 `fields.py`。

### 方案 B：只拷贝 Token 管理部分

需要的文件：`file_lock.py`、`token_refresh_scheduler.py`，以及 `tencent_client.py` 中和 Token 相关的方法。如果不想带上报修表的业务逻辑，可以用下面这个**独立的单文件版本**，只依赖 `httpx`：

```python
"""tdoc_token.py —— 腾讯文档 OAuth Token 管理（单文件，可直接拷贝）"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import httpx

OAUTH_BASE = "https://docs.qq.com/oauth/v2"


class TDocTokenManager:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 token_file: str | Path = "token.json", refresh_before_sec: int = 3 * 86400):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file = Path(token_file)
        self.refresh_before_sec = refresh_before_sec
        self.data: dict = json.loads(self.token_file.read_text("utf-8")) if self.token_file.exists() else {}

    # ---------- 首次授权 ----------
    def authorize_url(self, state: str = "init") -> str:
        return str(httpx.URL(f"{OAUTH_BASE}/authorize", params={
            "client_id": self.client_id, "redirect_uri": self.redirect_uri,
            "response_type": "code", "scope": "all", "state": state,
        }))

    def exchange_code(self, code: str) -> dict:
        return self._token_request({
            "grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri,
        })

    # ---------- 续期 ----------
    def refresh(self) -> dict:
        if not self.data.get("refresh_token"):
            raise RuntimeError("没有 refresh_token，只能重新授权")
        # ⚠️ 刷新参数按标准 OAuth2 推断，请对照官方文档核实
        return self._token_request({
            "grant_type": "refresh_token", "refresh_token": self.data["refresh_token"],
        })

    def get_access_token(self) -> str:
        """每次调用 API 前调用它：快过期就先刷新。"""
        exp = self._jwt_exp(self.data.get("access_token", ""))
        if exp is not None and exp - time.time() < self.refresh_before_sec and self.data.get("refresh_token"):
            self.refresh()
        return self.data["access_token"]

    def auth_headers(self) -> dict[str, str]:
        return {
            "Access-Token": self.get_access_token(),
            "Client-Id": self.client_id,
            "Open-Id": self.data["open_id"],
        }

    # ---------- 内部 ----------
    def _token_request(self, extra: dict) -> dict:
        params = {"client_id": self.client_id, "client_secret": self.client_secret, **extra}
        resp = httpx.get(f"{OAUTH_BASE}/token", params=params, timeout=30)
        body = resp.json()
        if resp.status_code >= 400 or "access_token" not in body:
            raise RuntimeError(f"获取 token 失败: {body}")
        self.data["access_token"] = body["access_token"]
        # 返回了新 refresh_token 就替换，否则沿用旧的
        self.data["refresh_token"] = body.get("refresh_token") or self.data.get("refresh_token", "")
        self.data["open_id"] = body.get("user_id") or self.data.get("open_id", "")
        self.data["updated_at"] = int(time.time())
        tmp = self.token_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.token_file)  # 原子替换，避免写一半被读到
        return body

    @staticmethod
    def _jwt_exp(token: str) -> float | None:
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
        except Exception:
            return None
```

使用示例：

```python
tm = TDocTokenManager(CLIENT_ID, CLIENT_SECRET, "https://你的域名/oauth/callback")

# 首次：把链接发给表格所有者，回调里拿到 code 后
print(tm.authorize_url())
tm.exchange_code(code)

# 之后每次调 API：
resp = httpx.get("https://docs.qq.com/openapi/drive/v2/util/converter",
                 params={"type": 2, "value": "表格encodedID"},
                 headers=tm.auth_headers())
if resp.status_code == 401:      # 兜底：被动过期
    tm.refresh()
    resp = httpx.get(..., headers=tm.auth_headers())
```

这个单文件版本与本项目实现的区别：

- 它采用“调用前检查是否快过期”的懒刷新，不需要后台定时任务，适合脚本或 Web 请求类项目。
- 写文件时先写临时文件再原子替换，只适合**单进程**使用。多个进程共享同一个 `token.json` 时，请改用本项目的 `file_lock.py`，否则两个进程可能同时刷新，其中一个会拿着已失效的 refresh_token。

### 方案 C：其他语言（Java / Node / Go）

逻辑只有三个 HTTP GET 加一次 JWT 解析，照第 2 节的接口表翻译即可。要点：

1. `client_secret` 只能放在服务端，换 Token 和刷新都必须在后端发起。
2. 持久化 `access_token`、`refresh_token`、`open_id`，缺一不可。
3. 调 API 时带 `Access-Token`、`Client-Id`、`Open-Id` 三个 Header。
4. 同时实现“到期前主动刷新”和“401 被动刷新”两条路径。

---

## 7. 给他人使用时的注意事项

- **不要共享你的 token.json**：Token 代表授权人本人的腾讯文档权限（`scope=all`），谁拿到都能读写该账号可访问的所有文档。其他项目应该**用他们自己的 Client ID 注册应用，由他们自己的账号授权**。
- **不要把 `.env` 或 `token.json` 提交到 Git**：本仓库 `.gitignore` 现已忽略 `.env`、`tencent-doc-filler/token.json` 和 `next_row.json`。但 token.json 曾被提交进首个 commit，**git 历史里仍然有旧 Token**，因此必须重新授权。如果仓库公开过，还应清理历史，或把仓库改为私有。另外，项目中已有的 `腾讯文档API接口与Token配置指南.md` 等文档里写着完整的 Access Token 和 Client ID，对外分享前应先脱敏。
- **Open ID 可能变化**：用户绑定或解绑账号后 Open ID 会变化，此时需要重新授权。
- **授权人离职或换号**：Token 跟人走。建议使用一个专门的“服务账号”QQ 授权，并把目标表格共享给它。
- **监控**：`GET /health` 中的 `has_refresh_token` 应为 `true`。若日志出现 `Token 自动刷新失败`，说明 refresh_token 已失效，需要重新授权。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `/oauth/callback` 返回 401 或“换取 token 失败” | code 超过 5 分钟或已用过 | 重新打开授权链接，拿新 code |
| `has_refresh_token: false` | 换 Token 时接口没有返回 refresh_token，或 Token 是手工填进 `.env` 的 | 按第 5 节走完整授权；如果接口仍不返回，到开放平台确认应用权限 |
| 日志出现 `无法解析 Access Token 过期时间` | Token 不是 JWT 格式 | 不影响使用，依靠 401 兜底刷新 |
| 刷新后另一个进程报 401 | 多进程各自缓存了旧 Token | 让所有进程共享同一个 `token.json`，并在 401 时重新读取文件 |
